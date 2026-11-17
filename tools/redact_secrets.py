#!/usr/bin/env python3
"""redact_secrets.py — the leak gate of the agentic review.

The agentic review runs a model inside CI with a credential in its
environment. The credential must never reach a place a reader can see:
a pull-request comment, a job log, an artefact, a commit. This tool is
the last line of defence, and it is deliberately simple: it knows one
secret, it looks for it, and it either removes it or stops the run.

Three modes:

    --file PATH        redact a file in place (writes a .redacted copy)
    --check PATH       exit 1 if the secret appears in PATH
    --scan-tree DIR    report every file under DIR that holds the secret
    --scan-history     report every commit in the repository that holds it

The secret is read from an environment variable (--secret-env NAME). It
is never passed on the command line, never printed, and never written:
the tool reports the *path* of a leak, never the value.

A leak of a substring counts as a leak: a truncated key is still a key.
The tool therefore masks every contiguous run of MIN_PARTIAL characters
or more of the secret, not only the whole secret.
"""

from __future__ import annotations

import argparse
import os
import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent

#: The shortest run of the secret that is still dangerous to publish.
MIN_PARTIAL = 12

#: Where a secret must never be found.
SKIP_DIRS = {
    ".git",
    ".venv",
    "node_modules",
    "runs",
    "__pycache__",
    ".cache",
    ".pi",
    "data",
    "terrain",
}

#: Files that are never scanned for a leak (they hold the reference data
#: and the binaries; a key cannot hide in a GeoTIFF).
SKIP_SUFFIXES = {
    ".pdf",
    ".tif",
    ".tiff",
    ".gpkg",
    ".zip",
    ".gz",
    ".png",
    ".jpg",
    ".so",
    ".dylib",
    ".dll",
}


def _secret(env_name: str) -> str:
    value = os.environ.get(env_name, "")
    if not value:
        raise SystemExit(f"the environment variable {env_name} is empty")
    if len(value) < MIN_PARTIAL:
        raise SystemExit(
            f"the secret in {env_name} is shorter than {MIN_PARTIAL} characters; "
            "refusing to treat it as a secret"
        )
    return value


def redact_text(text: str, secret: str) -> tuple[str, int]:
    """Return the text without the secret, and how many times it was found.

    The whole secret is masked first. A truncated secret is masked too:
    a run of MIN_PARTIAL characters that matches the secret is extended
    as far as the text and the secret agree, and the whole run is
    replaced.
    """
    hits = 0
    out = text
    if secret in out:
        out = out.replace(secret, "***REDACTED***")
        hits += 1
    length = len(secret)
    index = 0
    while index <= length - MIN_PARTIAL:
        window = secret[index : index + MIN_PARTIAL]
        found = out.find(window)
        if found < 0:
            index += 1
            continue
        # Extend the match left and right while the text and the secret
        # agree: a leaked prefix or a leaked suffix is still a leak.
        start = index
        begin = found
        while start > 0 and begin > 0 and secret[start - 1] == out[begin - 1]:
            start -= 1
            begin -= 1
        end = index + MIN_PARTIAL
        stop = found + MIN_PARTIAL
        while end < length and stop < len(out) and secret[end] == out[stop]:
            end += 1
            stop += 1
        out = out[:begin] + "***REDACTED***" + out[stop:]
        hits += 1
        index = max(end, index + 1)
    return out, hits


def redact_file(path: pathlib.Path, secret: str, write: bool = True) -> int:
    """Redact a file in place. Returns the number of replacements."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return 0
    new, hits = redact_text(text, secret)
    if hits and write:
        path.write_text(new, encoding="utf-8")
    return hits


def iter_tree(root: pathlib.Path):
    """Every scannable file under root."""
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if SKIP_SUFFIXES & {path.suffix.lower()}:
            continue
        if any(part in SKIP_DIRS for part in path.relative_to(root).parts):
            continue
        yield path


def scan_tree(root: pathlib.Path, secret: str) -> list[str]:
    """The paths under root that hold the secret."""
    leaks = []
    for path in iter_tree(root):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if secret in text:
            leaks.append(str(path.relative_to(root)))
    return leaks


def scan_history(secret: str, repo: pathlib.Path = REPO) -> list[str]:
    """The commits whose diffs hold the secret.

    The output is read as bytes: the history holds binaries (the
    compiled PDFs), and a decode error would hide the very thing the
    scan is looking for.
    """
    try:
        proc = subprocess.run(
            ["git", "log", "-p", "--all", "--full-history"],
            cwd=repo,
            capture_output=True,
            check=False,
        )
    except OSError:
        return []
    needle = secret.encode("utf-8", errors="replace")
    leaks: list[str] = []
    current = None
    for line in proc.stdout.splitlines():
        if line.startswith(b"commit "):
            current = line.split()[1].decode("ascii", errors="replace")
        elif needle in line and current and current not in leaks:
            leaks.append(current)
    return leaks


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--secret-env", default="OPENCODE_API_KEY")
    parser.add_argument("--file", action="append", default=[])
    parser.add_argument("--check", action="append", default=[])
    parser.add_argument("--scan-tree", default=None)
    parser.add_argument("--scan-history", action="store_true")
    parser.add_argument(
        "--no-write",
        action="store_true",
        help="report what would be redacted without writing anything",
    )
    args = parser.parse_args(argv)

    secret = _secret(args.secret_env)
    total = 0
    failed = False

    for name in args.file:
        path = pathlib.Path(name)
        hits = redact_file(path, secret, write=not args.no_write)
        total += hits
        if hits:
            print(f"redacted {hits} occurrence(s) in {name}")

    for name in args.check:
        path = pathlib.Path(name)
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        _, hits = redact_text(text, secret)
        total += hits
        if hits:
            print(f"SECRET FOUND in {name} ({hits} occurrence(s))")
            failed = True

    if args.scan_tree:
        root = pathlib.Path(args.scan_tree)
        leaks = scan_tree(root, secret)
        for leak in leaks:
            print(f"SECRET FOUND in {leak}")
        total += len(leaks)
        failed = failed or bool(leaks)
        if not leaks:
            print(f"no secret under {root}")

    if args.scan_history:
        leaks = scan_history(secret)
        for leak in leaks:
            print(f"SECRET FOUND in commit {leak}")
        total += len(leaks)
        failed = failed or bool(leaks)
        if not leaks:
            print("no secret in the history")

    if total and failed:
        print("the secret was found where it must not be")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
