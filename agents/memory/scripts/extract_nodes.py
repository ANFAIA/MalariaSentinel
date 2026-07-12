#!/usr/bin/env python3
# Filter for reembed.sh: takes JSON from neo4j-cli, emits one line per
# Entity node with "|||" as field separator, newlines escaped as \n,
# and "|||" replaced with "___" to avoid breaking the field separator.
import json
import sys

d = json.load(sys.stdin)
for r in d["rows"]:
    u = r["uuid"]
    n = r["name"]
    s = r["summary"] or ""
    s = s.replace("\\", "\\\\").replace("\n", "\\n").replace("|||", "___")
    print(f"{u}|||{n}|||{s}")
