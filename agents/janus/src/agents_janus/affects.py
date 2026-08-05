"""Affects graph — reads 'affects' blocks from spec YAML frontmatter."""
from __future__ import annotations
from pathlib import Path
import yaml

def load_affects(spec_path: Path) -> dict[str, list[str]]:
    """Load the affects block from a spec's YAML frontmatter.
    
    Returns: {"component_name": ["affected_spec_path", ...], ...}
    """
    if not spec_path or not spec_path.exists():
        return {}
    text = spec_path.read_text()
    # Extract YAML frontmatter between --- markers
    if not text.startswith("---"):
        return {}
    end = text.find("---", 3)
    if end == -1:
        return {}
    frontmatter = yaml.safe_load(text[3:end])
    return frontmatter.get("affects", {}) if isinstance(frontmatter, dict) else {}

def get_affected_specs(spec_path: Path, all_spec_paths: list[Path]) -> list[Path]:
    """Given a spec, return which other specs it affects."""
    affects = load_affects(spec_path)
    if not affects:
        return []
    affected_names = set()
    for targets in affects.values():
        affected_names.update(targets)
    
    result = []
    for sp in all_spec_paths:
        # Match by directory name (e.g., "abm" matches docs/specs/abm/spec.md)
        if sp.parent.name in affected_names:
            result.append(sp)
    return result


# ── Compose notifications (M16) ──────────────────────────────────────

def compose_affected_notifications(changed_spec: str, registry) -> list[dict]:
    """When docs/specs/X/spec.md changes, find all specs that declare
    affects: [X] and return mailbox messages for them."""
    all_spec_paths = []
    for name, spec in registry.all().items():
        if spec.spec_path:
            all_spec_paths.append(Path(spec.spec_path))

    affected = get_affected_specs(Path(changed_spec), all_spec_paths)
    return [
        {
            "to": spec.name if hasattr(spec, "name") else str(sp.parent.name),
            "from": "affects-watcher",
            "re": f"spec {changed_spec} changed",
            "severity": "non-breaking",
            "ask": "ack",
        }
        for sp in affected
        for spec in [registry.get(sp.parent.name)] if hasattr(registry, 'get')
    ]
