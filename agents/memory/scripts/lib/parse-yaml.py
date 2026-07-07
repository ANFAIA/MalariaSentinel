#!/usr/bin/env python3
# Module: agents/memory — see AGENTS.md (Protected files) and opencode.json permission.edit.
#
# agents/memory/scripts/lib/parse-yaml.py
# Parse a seed-style yaml file (same shape as tools/memory/seed/<project>.yaml
# and tools/memory/bootstrap/*.yaml) and emit a flat representation that the
# shell scripts can consume.
#
# Usage:
#   parse-yaml.py <yaml_file> <output_dir>
#
# Output files in <output_dir> (one record per line, tab-separated):
#   project          — single line, the declared project name (or empty)
#   group_id         — single line, the declared group_id (or empty)
#   components       — uuid\tname\tsummary\tpath
#   investigations   — uuid\tname\tsummary\tstatus\tpath
#   pitfalls         — uuid\tname\tsummary\tpath
#   preferences      — uuid\tname\tsummary\tpath
#   architectures    — uuid\tname\tsummary\tpath
#   tools            — uuid\tname\tsummary\tpath
#   patterns         — uuid\tname\tsummary\tpath
#   operational      — uuid\tname\tsummary\tpath
#   relations        — src\ttype\tdst\tprops
#
# A "record" with empty uuid is silently skipped by the consumer.
#
# The yaml format is described in seed.config.example.yaml. This script
# is the single source of truth for the grammar; the shell scripts
# (seed.sh, bootstrap-apply.sh) just call it.

import os
import re
import sys


def parse_item(item_lines):
    d = {}
    if not item_lines:
        return d
    first = item_lines[0]
    m = re.match(r"^\s*([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$", first)
    if m and m.group(2):
        d[m.group(1)] = m.group(2).strip().strip('"').strip("'")
        i = 1
    else:
        i = 0
    while i < len(item_lines):
        s = item_lines[i]
        ms = re.match(r"^(\s*)([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$", s)
        if not ms:
            i += 1
            continue
        key, val = ms.group(2), ms.group(3)
        key_indent = len(ms.group(1))
        if val == "|":
            i += 1
            buf = []
            block_indent = key_indent + 2
            while i < len(item_lines):
                s2 = item_lines[i]
                stripped = s2.strip()
                if not stripped:
                    i += 1
                    continue
                line_indent = len(s2) - len(s2.lstrip(" "))
                if line_indent < block_indent:
                    break
                buf.append(stripped)
                i += 1
            d[key] = " ".join(b for b in buf if b)
        elif val == "":
            i += 1
        else:
            d[key] = val.strip().strip('"').strip("'")
            i += 1
    return d


def parse_relation(item_lines):
    text = " ".join(item_lines)
    d = {}
    for m in re.finditer(r"([A-Za-z_][A-Za-z0-9_]*):\s*([^,}\s][^,}]*)", text):
        d[m.group(1)] = m.group(2).strip().strip('"').strip("'")
    return d


def main():
    if len(sys.argv) != 3:
        print("usage: parse-yaml.py <yaml_file> <output_dir>", file=sys.stderr)
        sys.exit(2)
    yaml_path = sys.argv[1]
    out_dir = sys.argv[2]
    os.makedirs(out_dir, exist_ok=True)

    with open(yaml_path) as f:
        text = f.read()

    lines = []
    for raw in text.splitlines():
        s = raw.rstrip()
        if not s or s.lstrip().startswith("#"):
            continue
        lines.append(s)

    top = {}
    top_scalars = {}
    i = 0
    while i < len(lines):
        line = lines[i]
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$", line)
        if not m:
            i += 1
            continue
        key, val = m.group(1), m.group(2)
        if val == "":
            i += 1
            items = []
            while i < len(lines):
                s = lines[i]
                if re.match(r"^[A-Za-z_][A-Za-z0-9_]*:", s):
                    break
                m2 = re.match(r"^\s*-\s*(.*)$", s)
                if m2:
                    first = m2.group(1).strip()
                    item_lines = []
                    if first:
                        item_lines.append(first)
                    i += 1
                    while i < len(lines):
                        s2 = lines[i]
                        if re.match(r"^\s*-\s", s2) or re.match(r"^[A-Za-z_][A-Za-z0-9_]*:", s2):
                            break
                        item_lines.append(s2)
                        i += 1
                    items.append(item_lines)
                    continue
                i += 1
            top[key] = items
        else:
            top_scalars[key] = val.strip().strip('"').strip("'")
            i += 1

    def emit(label, yaml_key, dest_file, is_relation=False):
        items = top.get(yaml_key, [])
        out_lines = []
        for il in items:
            if is_relation:
                d = parse_relation(il)
                out_lines.append("\t".join([
                    d.get("src", ""),
                    d.get("type", ""),
                    d.get("dst", ""),
                    d.get("props", ""),
                ]))
            else:
                d = parse_item(il)
                if label == "Investigation":
                    out_lines.append("\t".join([
                        d.get("uuid", ""),
                        d.get("name", ""),
                        d.get("summary", ""),
                        d.get("status", ""),
                        d.get("path", ""),
                    ]))
                else:
                    out_lines.append("\t".join([
                        d.get("uuid", ""),
                        d.get("name", ""),
                        d.get("summary", ""),
                        d.get("path", ""),
                    ]))
        with open(os.path.join(out_dir, dest_file), "w") as f:
            f.write("\n".join(out_lines) + ("\n" if out_lines else ""))

    with open(os.path.join(out_dir, "project"), "w") as f:
        f.write(f"{top_scalars.get('project', '')}\n")
    with open(os.path.join(out_dir, "group_id"), "w") as f:
        f.write(f"{top_scalars.get('group_id', '')}\n")

    emit("Component", "components", "components")
    emit("Investigation", "investigations", "investigations")
    emit("Pitfall", "pitfalls", "pitfalls")
    emit("Preference", "preferences", "preferences")
    emit("Architecture", "architectures", "architectures")
    emit("Tool", "tools", "tools")
    emit("Pattern", "patterns", "patterns")
    emit("Operational", "operational", "operational")
    emit("Relation", "relations", "relations", is_relation=True)


if __name__ == "__main__":
    main()
