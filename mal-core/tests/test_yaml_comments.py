"""Contract test: every leaf of model_constants.yaml is documented.

R3: the YAML comment is the single place where a model constant is
explained. A leaf is a mapping entry whose value is a scalar or a
sequence, plus each member of a flow mapping (``weights``, ``pref``).

Coverage heuristic (stable, documented, and strict on purpose):

* INLINE — a ``#`` comment on the key's own line (quotes respected, so a
  ``#`` inside a string is not a comment);
* SEQUENCE SPAN — for a flow/block sequence that spans several lines, a
  comment on any line of its value span;
* FLOW-MAP CLOSE — for a member of a multi-line flow mapping, a comment on
  the mapping's closing line (the shared design used by ``weights``);
  a comment on a *sibling's* line does NOT cover the member;
* PREVIOUS LINE — an indented comment block immediately above the key (no
  blank line between them), indented at least as deep as the key. This
  rejects column-0 section headers, which are not field documentation.

The covering comment must contain a ``[unit]`` token. The number of leaves
is derived from the YAML, never frozen here: adding a documented key with
its comment does not break this test.
"""
from __future__ import annotations

from pathlib import Path

import yaml

YAML_PATH = (Path(__file__).resolve().parents[1]
             / "config" / "model_constants.yaml")

UNIT_RE = r"\[[^\]]+\]"


# --------------------------------------------------------------------------
# YAML helpers
# --------------------------------------------------------------------------
def _comments(raw: str) -> dict[int, tuple[str, int]]:
    """Map 0-based line -> (comment text, '#' column), quotes respected."""
    found: dict[int, tuple[str, int]] = {}
    for idx, line in enumerate(raw.splitlines()):
        in_single = in_double = False
        esc = False
        for col, ch in enumerate(line):
            if in_double:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    in_double = False
                continue
            if in_single:
                if ch == "'":
                    # YAML escapes a single quote by doubling it.
                    if col + 1 < len(line) and line[col + 1] == "'":
                        continue
                    in_single = False
                continue
            if ch == '"':
                in_double = True
            elif ch == "'":
                in_single = True
            elif ch == "#" and (col == 0 or line[col - 1] in " \t"):
                found[idx] = (line[col + 1:], col)
                break
    return found


def _leaves(raw: str):
    """Return (key, key_line, value_node, flow_map_close_line|None).

    A flow mapping (``weights: {a: 0.4, b: 0.1}``) is expanded into one leaf
    per member, so every member needs its own documentation (the shared
    mapping-level comment on the closing line is the accepted design).
    """
    root = yaml.compose(raw)
    out = []

    def walk(mapping):
        for key, value in mapping.value:
            if isinstance(value, yaml.MappingNode) and not value.flow_style:
                walk(value)
                continue
            if isinstance(value, yaml.MappingNode) and value.flow_style:
                for sub_key, sub_value in value.value:
                    out.append((sub_key.value, sub_key.start_mark.line,
                                sub_value, value.end_mark.line))
                continue
            out.append((key.value, key.start_mark.line, value, None))

    walk(root)
    return out


def _covered(key_line, value, close_line, comments, raw_lines):
    def has_unit(ln, after_col=None):
        item = comments.get(ln)
        if item is None:
            return False
        text, col = item
        if after_col is not None and col <= after_col:
            return False
        import re
        return bool(re.search(UNIT_RE, text))

    # 1. inline on the key line
    if has_unit(key_line):
        return True
    # 2. any line of the value span (sequences and single-line scalars).
    #    A block scalar is opaque text: a "# [u]" inside it is payload, not
    #    documentation, so its continuation lines are never scanned.
    block_scalar = (isinstance(value, yaml.ScalarNode)
                    and value.style in ("|", ">"))
    span_end = value.start_mark.line if block_scalar else value.end_mark.line
    for ln in range(value.start_mark.line, span_end + 1):
        if has_unit(ln):
            return True
    # 3. multi-line flow mapping: a comment AFTER the closing brace is the
    #    mapping-level comment shared by its members; a comment before the
    #    brace belongs to the sibling on that line and must not cover them.
    if close_line is not None and close_line != value.end_mark.line:
        brace_col = raw_lines[close_line].rfind("}")
        if has_unit(close_line, after_col=brace_col):
            return True
    # 4. indented comment block immediately above, no blank line, never a
    #    column-0 section header
    ln = key_line - 1
    block = []
    while ln >= 0 and comments.get(ln) is not None:
        text, col = comments[ln]
        # only standalone comment lines document the next key; an inline
        # comment after a sibling's value belongs to that sibling.
        if raw_lines[ln][:col].strip():
            break
        block.append(ln)
        ln -= 1
    if block and ln == key_line - 1 - len(block):
        key_indent = len(raw_lines[key_line]) - len(
            raw_lines[key_line].lstrip())
        for cl in block:
            indent = len(raw_lines[cl]) - len(raw_lines[cl].lstrip())
            if key_indent == 0 or indent < key_indent:
                return False
        return any(has_unit(cl) for cl in block)
    return False


def undocumented(raw: str) -> list[tuple[int, str]]:
    comments = _comments(raw)
    lines = raw.splitlines()
    missing = []
    for key, key_line, value, close in _leaves(raw):
        if not _covered(key_line, value, close, comments, lines):
            missing.append((key_line + 1, key))
    return missing


# --------------------------------------------------------------------------
# Contract
# --------------------------------------------------------------------------
def test_every_leaf_has_a_unit_comment():
    raw = YAML_PATH.read_text(encoding="utf-8")
    leaves = _leaves(raw)
    assert leaves, "model_constants.yaml has no leaves"
    missing = undocumented(raw)
    assert missing == [], (
        f"{len(missing)}/{len(leaves)} leaf keys lack a [unit] comment: "
        f"{missing}")


def test_missing_comment_is_detected():
    raw = "a:\n  b: 1\n  c: 2  # [u] ok\n"
    assert undocumented(raw) == [(2, "b")]


def test_comment_without_unit_is_detected():
    raw = "a:\n  b: 1  # no unit here\n"
    assert undocumented(raw) == [(2, "b")]


def test_flow_map_sibling_comment_does_not_cover():
    # b's inline comment must not document a or c.
    raw = ("w: {a: 1,\n"
           "    b: 2,  # [f] only b\n"
           "    c: 3}\n")
    assert undocumented(raw) == [(1, "a"), (3, "c")]


def test_flow_map_close_comment_covers_members():
    raw = ("w: {a: 1,\n"
           "    b: 2}  # [f] shared mapping comment\n")
    assert undocumented(raw) == []


def test_section_header_is_not_field_documentation():
    raw = "# [m] section-level header\na: 1\n"
    assert undocumented(raw) == [(2, "a")]


def test_indented_previous_line_comment_is_accepted():
    raw = "s:\n  # [u] field doc\n  a: 1\n"
    assert undocumented(raw) == []


def test_previous_line_comment_after_blank_line_is_rejected():
    raw = "s:\n  # [u] floated header\n\n  a: 1\n"
    assert undocumented(raw) == [(4, "a")]


def test_block_scalar_hash_is_not_a_comment():
    # The "# [u]" is the scalar's payload, not documentation of `a`.
    raw = "s:\n  a: |\n    # [u] inside scalar\n    text\n  b: 2  # [u] ok\n"
    assert undocumented(raw) == [(2, "a")]


def test_hash_inside_quotes_is_not_a_comment():
    raw = 's:\n  a: "x# [m] not a comment"\n'
    assert undocumented(raw) == [(2, "a")]
