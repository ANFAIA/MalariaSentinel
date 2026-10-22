"""Audit: model constants echoed inside comments/docstrings (task-04).

R3 says a model value is explained in ONE place: its comment in
``mal-core/config/model_constants.yaml``. Migrated code must not restate
values, units-with-values, provenance strings or ``NAME = value`` constant
literals in comments.

Two checks run over every comment/docstring line in the repo:

  A. VALUE ECHO — the line contains a number token that exactly equals a
     numeric leaf of mal-core/config/model_constants.yaml (or a
     percentage mapped to its fraction) AND a unit/context keyword
     (m, km, mm, °C, psu, día/day, per day, ...).
  B. CONSTANT / VARIABLE ASSIGNMENT — the line contains an identifier
     assigned a number (NAME = value, name = value). An ALL-CAPS name is
     always reported (it reads as a constant); a lowercase name is
     reported when the number is a YAML leaf value (state variables set
     to 0/1 are usually not).

Scope: the repository code. Artifacts are excluded BY PATH, never by bare
directory name — a Python package called ``data`` (the loaders) must be
scanned. The excluded top-level entries are ``docs/``, ``plans/``,
``.opencode/``, ``data/``, ``runs/``, ``papers/`` and ``terrain/`` (repo
root only), plus caches and build output by name.

Test files are scanned but counted separately: their fixtures legitimately
cite values as test data (R3 governs production documentation), so they are
accepted by path and the count is printed, never hidden.

Usage:
    python3 tools/audit_comment_constants.py            # whole repo
    python3 tools/audit_comment_constants.py --stats    # + raw/accepted counts
    python3 tools/audit_comment_constants.py path ...   # extra/alternative roots

Exit code 0 when the residual (non-allowlisted) hits are zero.
"""
from __future__ import annotations

import ast
import os
import re
import sys
import tokenize
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
YAML_PATH = REPO / "mal-core" / "config" / "model_constants.yaml"
ALLOWLIST_PATH = Path(__file__).with_name("comment_audit_allowlist.txt")

# Repo-root entries that are documentation/artifacts, not shipped code.
# Matched against the path RELATIVE to REPO, so any nested directory that
# happens to be named "data" (e.g. mal_commonlib/data/loaders) is scanned.
EXCLUDE_TOP = {
    "docs", "plans", ".opencode", "data", "runs", "papers", "terrain",
}
# Technical/cache directories, by name, anywhere.
EXCLUDE_NAMES = {
    ".git", ".gitagent", ".venv", "venv", "node_modules", "__pycache__",
    "build", "dist", ".pytest_cache", ".ruff_cache", ".mypy_cache",
    "site-packages", "htmlcov",
}

NUM_RE = re.compile(r"-?\d+(?:\.\d+)?")
ASSIGN_RE = re.compile(r"\b([A-Za-z_]\w*)\s*=\s*(-?\d+(?:\.\d+)?)")
UNIT_WORDS = re.compile(
    r"(\[m\]|\[mm\]|\[km\]|\[°c\]|\[psu\]|\[h\]|\[días\]|\[dias\]|\[1/día\]|"
    r"\[fracción\]|\[ind·|\[grados-día\]|\[huevos|\[m/s\]|\[m/°\]|"
    r"\bm\b|\bkm\b|\bmm\b|°c|deg c|\bpsu\b|\bdías?\b|\bdays?\b|m/s|"
    r"per day|/day|/día|por día|grados-día|eggs?,|huevos|%)",
    re.IGNORECASE)


def yaml_values(obj, out=None):
    if out is None:
        out = set()
    if isinstance(obj, dict):
        for v in obj.values():
            yaml_values(v, out)
    elif isinstance(obj, list):
        for v in obj:
            yaml_values(v, out)
    elif isinstance(obj, (int, float)) and not isinstance(obj, bool):
        out.add(float(obj))
    return out


def allowlist():
    patterns = []
    for line in ALLOWLIST_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            patterns.append(re.compile(line, re.IGNORECASE))
    return patterns


def docstring_lines(tree):
    lines = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef,
                             ast.AsyncFunctionDef)):
            body = node.body
            if body and isinstance(body[0], ast.Expr) \
               and isinstance(body[0].value, ast.Constant) \
               and isinstance(body[0].value.value, str):
                ds = body[0].value
                lines.update(range(ds.lineno,
                                   ds.lineno + len(ds.value.splitlines())))
    return lines


def py_units(path):
    raw = path.read_text(encoding="utf-8", errors="replace")
    try:
        tree = ast.parse(raw)
    except SyntaxError:
        return
    ds = docstring_lines(tree)
    src = raw.splitlines()
    with path.open("rb") as fh:
        try:
            toks = list(tokenize.tokenize(fh.readline))
        except tokenize.TokenError:
            toks = []
    for tok in toks:
        if tok.type == tokenize.COMMENT:
            yield tok.start[0], tok.string
    for ln in ds:
        if 0 < ln <= len(src):
            yield ln, src[ln - 1]


def cpp_units(path):
    """Yield (line, comment_text) for C/C++ comments only.

    Only the comment text is audited, never the code on the same line: an
    enum definition (``DAY = 0, // 06:00-18:00``) is code, and its value is
    not a model constant echoed in prose.
    """
    in_block = False
    for ln, line in enumerate(
            path.read_text(encoding="utf-8", errors="replace").splitlines(),
            start=1):
        parts = []
        i = 0
        quote = ""
        while i < len(line):
            ch = line[i]
            if in_block:
                end = line.find("*/", i)
                if end == -1:
                    parts.append(line[i:])
                    i = len(line)
                else:
                    parts.append(line[i:end])
                    in_block = False
                    i = end + 2
                continue
            if quote:
                if ch == "\\":
                    i += 2
                    continue
                if ch == quote:
                    quote = ""
                i += 1
                continue
            if ch in ("'", '"'):
                quote = ch
                i += 1
                continue
            if line.startswith("//", i):
                parts.append(line[i + 2:])
                break
            if line.startswith("/*", i):
                in_block = True
                i += 2
                continue
            i += 1
        text = " ".join(parts).strip()
        if text:
            yield ln, text


def is_test_file(path):
    """Test fixtures legitimately cite values as test data (R3 is about
    production documentation), so test paths are accepted by path, not by a
    regex that could hide a production hit."""
    return "tests" in path.parts or path.name.startswith("test_")


def iter_files(roots):
    for root in roots:
        p = (REPO / root).resolve() if not Path(root).is_absolute() \
            else Path(root)
        if p.is_file():
            yield p
            continue
        for dp, dns, fns in os.walk(p):
            cur = Path(dp)
            dns[:] = [d for d in dns if _keep_dir(cur / d)]
            for fn in fns:
                if fn.endswith((".py", ".hpp", ".cpp", ".cc")):
                    yield cur / fn


def _keep_dir(path: Path) -> bool:
    if path.name in EXCLUDE_NAMES or path.name.startswith(".egg"):
        return False
    try:
        rel = path.resolve().relative_to(REPO)
    except ValueError:
        return True                      # external root (self-tests)
    return not (rel.parts and rel.parts[0] in EXCLUDE_TOP)


def main(argv):
    # The default is the repository root, not the current directory, so
    # running the tool from anywhere scans the same tree.
    roots = [a for a in argv[1:] if not a.startswith("--")] or [str(REPO)]
    values = yaml_values(yaml.safe_load(YAML_PATH.read_text(encoding="utf-8")))
    accepted = allowlist()
    residual = []
    test_hits = 0
    raw_hits = 0
    accepted_hits = 0
    accepted_files = set()
    accepted_test_files = set()
    accepted_test_hits = 0
    test_files = set()
    scanned = 0
    for path in sorted(iter_files(roots)):
        scanned += 1
        in_tests = is_test_file(path)
        gen = py_units(path) if path.suffix == ".py" else cpp_units(path)
        for ln, text in gen:
            echo = ""
            for tok in NUM_RE.findall(text):
                num = float(tok)
                # A percentage in a comment is the same leak as its fraction.
                pct = "%" in text and (num / 100.0) in values
                if num in values or pct:
                    echo = tok
                    break
            hit = ""
            for name, num in ASSIGN_RE.findall(text):
                upper = name.upper() == name and len(name) >= 3
                in_yaml = float(num) in values
                if upper or in_yaml:
                    hit = f"assignment:{name}={num}"
                    break
            if not hit and echo and UNIT_WORDS.search(text):
                hit = echo
            if not hit:
                continue
            raw_hits += 1
            if any(p.search(text) for p in accepted):
                accepted_hits += 1
                accepted_files.add(path)
                if in_tests:
                    accepted_test_hits += 1
                    accepted_test_files.add(path)
                continue
            if in_tests:
                test_hits += 1
                test_files.add(path)
                continue
            shown = os.path.relpath(path, REPO)
            residual.append(f"{shown}:{ln}:{hit}: {' '.join(text.split())}")
    for line in residual:
        print(line)
    if "--stats" in argv:
        print(f"stats: {raw_hits} raw hit line(s); {accepted_hits} allowlisted "
              f"in {len(accepted_files)} file(s) "
              f"({accepted_test_hits} of them in {len(accepted_test_files)} "
              f"test file(s)); {test_hits} test-fixture in "
              f"{len(test_files)} file(s); {len(residual)} residual")
    print(f"audit_comment_constants: {scanned} file(s) scanned, "
          f"{len(residual)} residual hit(s) outside the allowlist "
          f"({test_hits} fixture citation(s) in test files accepted by path)")
    return 1 if residual else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
