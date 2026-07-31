"""Spec loader — parses spec.md files and extracts sections for subagent prompts."""
from __future__ import annotations
import re
from pathlib import Path
import yaml

def load_spec_sections(spec_path: Path) -> dict[str, str]:
    """Load a spec.md file and extract sections by '## N. Title' headings.
    
    Returns: {"1 Objective": "text...", "2 In scope": "text...", ...}
    """
    if not spec_path or not spec_path.exists():
        return {}
    text = spec_path.read_text()
    
    # Split on '## N.' headings
    sections = {}
    pattern = re.compile(r'^## (\d+)\.?\s+(.+)$', re.MULTILINE)
    matches = list(pattern.finditer(text))
    
    for i, match in enumerate(matches):
        heading = f"{match.group(1)} {match.group(2).strip()}"
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        sections[heading] = text[start:end].strip()
    
    return sections

def load_spec_frontmatter(spec_path: Path) -> dict:
    """Load YAML frontmatter from a spec.md."""
    if not spec_path or not spec_path.exists():
        return {}
    text = spec_path.read_text()
    if not text.startswith("---"):
        return {}
    end = text.find("---", 3)
    if end == -1:
        return {}
    return yaml.safe_load(text[3:end]) or {}

def build_subagent_prompt(spec_path: Path, role_preamble: str = "") -> str:
    """Build a subagent system prompt from a spec.md.
    
    Concatenates: role preamble + sections 1-8 (Objective through Drift check).
    """
    sections = load_spec_sections(spec_path)
    
    parts = []
    if role_preamble:
        parts.append(role_preamble)
    
    # Include sections 1-6 and 8 (Objective through Drift check, skip 7 Implementation plan)
    for key in sorted(sections.keys()):
        num = key.split()[0]
        if num in ("1", "2", "3", "4", "5", "6", "8"):
            parts.append(f"## {key}\n{sections[key]}")
    
    return "\n\n".join(parts)
