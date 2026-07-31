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
