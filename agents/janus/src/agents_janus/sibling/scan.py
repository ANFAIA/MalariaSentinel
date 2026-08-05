"""SCAN markers — output-restoring anchors for forked sub-contexts."""
from __future__ import annotations

from enum import Enum


class ScanLevel(Enum):
    FULL = "full"      # 7 markers (~300 tokens)
    MINI = "mini"      # 3 markers (~100 tokens)
    ANCHOR = "anchor"  # 1 marker (~30 tokens)


SCAN_MARKERS_FULL = """\
## CONTEXT SCAN PROTOCOL
This prompt contains markers @@SCAN_1..@@SCAN_7. Before any task,
output answers in CHAT (visible text, not thinking).

### Sibling B's intent
@@SCAN_1: What sibling-B is about to do.

### My original goal
@@SCAN_2: The original task I was given (parent).

### Diff received
@@SCAN_3: What sibling-B changed (file path + symbol + lines).

### Adaptation options
@@SCAN_4: A) Adapt, B) Counter-propose, C) Both adapt.

### Rules at risk
@@SCAN_5: API contract preservation, no new files, no test changes.

### Failure mode
@@SCAN_6: Most likely way to break the parent task.

### Negotiation vocabulary
@@SCAN_7: Terms to use when proposing the common point.

After work, mandatory:
CHECK: <what was verified>
MISSED: <what was not verified> (or "MISSED: none")

Skip CHECK if trivial. Use ANCHOR (!) at start of long tasks.
"""

SCAN_MARKERS_MINI = """\
## CONTEXT SCAN PROTOCOL (MINI)
@@SCAN_1: Sibling-B's intent.
@@SCAN_2: My original goal.
@@SCAN_3: Diff received.

CHECK: <what was verified>
MISSED: <what was not verified>
"""

SCAN_MARKERS_ANCHOR = """\
## ANCHOR (!)
Focus on the original goal. Do not deviate.
"""


SCAN_MARKERS = SCAN_MARKERS_FULL


def get_scan_markers(level: ScanLevel = ScanLevel.FULL) -> str:
    """Return SCAN markers for the given level."""
    if level == ScanLevel.MINI:
        return SCAN_MARKERS_MINI
    elif level == ScanLevel.ANCHOR:
        return SCAN_MARKERS_ANCHOR
    return SCAN_MARKERS_FULL
