#!/usr/bin/env python3
"""Post-process the recall query output into the final JSON shape."""
import json
import sys

with open(sys.argv[1]) as f:
    d = json.load(f)

k_limit = int(sys.argv[2])
hits = []
for r in d.get("rows", []):
    hit = {
        "node": {
            "uuid":    r.get("uuid"),
            "name":    r.get("name"),
            "summary": r.get("summary"),
            "labels":  r.get("labels", []),
        },
        "score":         r.get("score"),
        "chain_to_root": r.get("chain") or [],
        "connected":     r.get("connected") or [],
    }
    hit["connected"] = [c for c in hit["connected"] if c.get("uuid")]
    if hit["node"]["summary"] and len(hit["node"]["summary"]) > 200:
        hit["node"]["summary"] = hit["node"]["summary"][:200] + "..."
    for c in hit["connected"]:
        if c.get("summary") and len(c["summary"]) > 200:
            c["summary"] = c["summary"][:200] + "..."
    hits.append(hit)

print(json.dumps({"hits": hits, "k_requested": k_limit, "k_returned": len(hits)}, indent=2, default=str))
