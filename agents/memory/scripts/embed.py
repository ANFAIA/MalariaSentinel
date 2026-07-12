#!/usr/bin/env python3
# agents/memory/scripts/embed.py
# Wraps OpenAI's text-embedding-3-small (1536d) for the project memory.
# Reads OPENAI_API_KEY from agents/memory/runtime/.env.
#
# Usage:
#   embed.py <text>                    # print JSON list of floats to stdout
#   embed.py --check                   # print "ok" if API key is reachable
#
# Output is a single line of compact JSON (no whitespace), suitable for
# piping into neo4j-cli --param via :embed modifier or via --param.

import json
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path

MODEL = "text-embedding-3-small"
DIM = 1536

# --- locate .env (project root or agents/memory/runtime/.env) ---
def _find_env() -> Path | None:
    d = Path(__file__).resolve().parent
    for _ in range(8):
        candidate = d / "runtime" / ".env"
        if candidate.is_file():
            return candidate
        d = d.parent
    return None

def _read_env_value(env_path: Path, key: str) -> str | None:
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            k, _, v = line.partition("=")
            if k.strip() == key:
                v = v.strip().strip('"').strip("'")
                return v or None
    return None

def get_api_key() -> str | None:
    env_path = _find_env()
    if env_path:
        k = _read_env_value(env_path, "OPENAI_API_KEY")
        if k:
            return k
    return os.environ.get("OPENAI_API_KEY")

def embed(text: str) -> list[float]:
    key = get_api_key()
    if not key:
        raise SystemExit("embed.py: OPENAI_API_KEY not set (checked runtime/.env and env)")
    base = os.environ.get("OPENAI_API_URL", "https://api.openai.com/v1")
    url = f"{base.rstrip('/')}/embeddings"
    body = json.dumps({
        "input": text,
        "model": MODEL,
    }).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            payload = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        raise SystemExit(f"embed.py: OpenAI HTTP {e.code} {e.reason}: {e.read().decode('utf-8', 'replace')}")
    except urllib.error.URLError as e:
        raise SystemExit(f"embed.py: cannot reach OpenAI: {e.reason}")
    vec = payload["data"][0]["embedding"]
    if len(vec) != DIM:
        raise SystemExit(f"embed.py: expected dim {DIM}, got {len(vec)}")
    return vec

def main(argv: list[str]) -> int:
    if len(argv) >= 2 and argv[1] == "--check":
        key = get_api_key()
        if not key:
            print("no-key")
            return 1
        # Light-weight probe: embed a single short string
        try:
            vec = embed("ping")
            print(f"ok dim={len(vec)}")
            return 0
        except SystemExit as e:
            print(f"error: {e}", file=sys.stderr)
            return 1
    if len(argv) < 2:
        print("Usage: embed.py <text> | --check", file=sys.stderr)
        return 2
    text = " ".join(argv[1:])
    vec = embed(text)
    print(json.dumps(vec, separators=(",", ":")))
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv))
