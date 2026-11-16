#!/usr/bin/env python3
"""Mechanical signals for the warnings-only coherence review.

The coherence review (``.github/workflows/coherence-review.yml``) is an
ADVISOR: it reports incoherences between the conceptual documents and the
implementation, and it never blocks. This script produces the mechanical
signals the reviewer may cite — it does not decide anything, and a signal
here is not a verdict.

Signals
-------
1. ``\\mskey{...}`` in a document vs the keys the generator emitted: a key
   the configuration no longer has.
2. ``\\code{...}`` identifiers vs the symbols that exist in the tree: a
   name the document mentions that nothing defines.
3. Paths named in a document (``docs/...``, ``papers/...``, ``scripts/...``,
   ``mal-*/...``) vs the tree: a path that no longer exists.
4. Contract versions mentioned in a document vs ``model_constants.yaml``.
5. Changed paths vs the stage documents that cover them: the candidate
   documents a reviewer should read.

Usage:
    uv run python tools/coherence_signals.py [--changed FILE ...] [--json]
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CONCEPTS = REPO / "docs" / "concepts"

MSKEY_RE = re.compile(r"\\mskey\{([^}]+)\}")
CODE_RE = re.compile(r"\\code\{([^}]+)\}")
PATH_RE = re.compile(
    r"\b((?:docs|papers|scripts|tools|mal-[a-z\-]+|data)/[A-Za-z0-9_\\\-\./]*[A-Za-z0-9_\-])"
)
VERSION_RE = re.compile(r"contract[^.\n]{0,40}?([0-9]+\.[0-9]+(?:\.[0-9]+)?)")

# Which document covers which area of the tree (stage ownership, plan D5).
STAGE_AREAS: dict[str, tuple[str, ...]] = {
    "download": ("mal-core/src/mal_core/download/", "mal-commonlib/src/mal_commonlib/data/"),
    "ingest": ("mal-core/src/mal_core/ingest/", "mal-core/src/mal_core/habitat/"),
    "abm": ("mal-core/src/mal_core/abm/",),
    "scoring": ("mal-core/src/mal_core/scoring/",),
    "training": ("mal-core/src/mal_core/training/",),
    "prediction": ("mal-core/src/mal_core/prediction/",),
}

DOC_FOR_STAGE = {
    "download": "docs/concepts/download/download.tex",
    "ingest": "docs/concepts/ingest/ingest.tex",
    "abm": "docs/concepts/abm/odd-2010-malariasentinel.tex",
    "scoring": "docs/concepts/scoring/scoring.tex",
    "training": "docs/concepts/training/training.tex",
    "prediction": "docs/concepts/prediction/prediction.tex",
}


def documents() -> list[Path]:
    if not CONCEPTS.is_dir():
        return []
    return sorted(
        p
        for p in CONCEPTS.glob("*/*.tex")
        if p.name not in {"odd-2010-template.tex"}
    )


def known_macro_keys() -> set[str]:
    macros = CONCEPTS / "generated" / "macros.tex"
    if not macros.exists():
        return set()
    text = macros.read_text(encoding="utf-8")
    return set(re.findall(r"\\csname ms@k@([^\\]+)\\endcsname", text))


SYMBOL_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.]*(?:\(\))?$")


def _LOOKS_LIKE_A_SYMBOL(token: str) -> bool:
    """Whether a ``\\code{...}`` token names a symbol rather than a pattern.

    A document writes patterns, file-name templates and JSON fragments
    inside ``\\code{...}`` too; only a plain identifier can be checked
    against the tree. A noisy signal is worse than none: the reviewer
    cites these, and noise costs the maintainer more than it saves.
    """
    if not token or len(token) < 4:
        return False
    if not SYMBOL_RE.match(token):
        return False
    if token.endswith("."):
        return False
    return True


def _mentioned_in_tree(symbol: str, tree: str) -> bool:
    """Whether a symbol (or its last component) appears in the tree."""
    if symbol in tree:
        return True
    tail = symbol.split(".")[-1].removesuffix("()")
    if not tail:
        return False
    return re.search(rf"\b{re.escape(tail)}\b", tree) is not None


def _unescape(text: str) -> str:
    """Undo the LaTeX escapes a path or symbol carries inside ``\\code{...}``."""
    # A long path is broken across lines with \allowbreak{}; the break is
    # not part of the path.
    text = re.sub(r"\\allowbreak\{\}", "", text)
    text = re.sub(r"\\linebreak\{\}", "", text)
    for esc, plain in (
        ("\\_", "_"),
        ("\\&", "&"),
        ("\\%", "%"),
        ("\\#", "#"),
        ("\\$", "$"),
        ("\\{", "{"),
        ("\\}", "}"),
        ("\\ ", " "),
    ):
        text = text.replace(esc, plain)
    return text


def tree_text() -> str:
    """The text of the tree a symbol or path must appear in."""
    parts: list[str] = []
    for pattern in ("*.py", "*.hpp", "*.cpp", "*.yaml", "*.md", "*.toml"):
        for path in REPO.glob(f"**/{pattern}"):
            rel = path.relative_to(REPO)
            if rel.parts[0] in {".git", ".venv", ".cache", ".gitagent", "node_modules"}:
                continue
            try:
                parts.append(path.read_text(encoding="utf-8", errors="ignore"))
            except OSError:
                continue
    return "\n".join(parts)


def changed_files(files: list[str]) -> list[str]:
    if files:
        return files
    try:
        out = subprocess.run(
            ["git", "diff", "--name-only", "origin/main...HEAD"],
            cwd=REPO,
            capture_output=True,
            text=True,
            check=False,
        ).stdout
    except OSError:
        return []
    return [line for line in out.splitlines() if line.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--changed", nargs="*", default=[], help="changed paths")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    report: dict[str, list[str]] = {
        "unknown_model_keys": [],
        "unknown_symbols": [],
        "missing_paths": [],
        "contract_versions": [],
        "candidate_documents": [],
    }

    macros = known_macro_keys()
    sections = {key.split(".")[0] for key in macros}
    tree = tree_text()
    tree_paths = {
        str(p.relative_to(REPO)) for p in REPO.rglob("*") if p.is_file()
    }
    tree_dirs = {
        str(p.relative_to(REPO)) for p in REPO.rglob("*") if p.is_dir()
    }

    for doc in documents():
        if doc.parent.name == "generated":
            # Generated fragments are built from the code; they are the
            # reference, not the thing to check.
            continue
        text = doc.read_text(encoding="utf-8")
        # A long path is broken across lines with \allowbreak; join it back
        # before looking for paths, or the signal reports a fragment.
        text = re.sub(r"\\allowbreak(\{\})?[ \t]*\n[ \t]*", "", text)
        text = text.replace("\\allowbreak{}", "")
        rel = doc.relative_to(REPO)

        for key in MSKEY_RE.findall(text):
            if key not in macros:
                report["unknown_model_keys"].append(f"{rel}: \\mskey{{{key}}}")

        for symbol in CODE_RE.findall(text):
            symbol = _unescape(symbol.strip())
            if not _LOOKS_LIKE_A_SYMBOL(symbol):
                continue
            parts = symbol.split(".")
            if len(parts) > 1 and parts[0] in sections:
                # A configuration key: check it against the generated macros.
                if symbol not in macros:
                    # A SECTION reference is legitimate prose (it carries no
                    # number); only an unknown LEAF is an error. And a name
                    # that is a code symbol (a function that shares a
                    # section's name) is a symbol, not a key.
                    if not any(k.startswith(symbol + ".") for k in macros):
                        if not _mentioned_in_tree(symbol, tree):
                            report["unknown_model_keys"].append(
                                f"{rel}: \\code{{{symbol}}}"
                            )
                continue
            if _mentioned_in_tree(symbol, tree):
                continue
            report["unknown_symbols"].append(f"{rel}: \\code{{{symbol}}}")

        for path in PATH_RE.findall(text):
            path = _unescape(path.rstrip(".,;"))
            if path in tree_paths or path in tree_dirs:
                continue
            if path.startswith("data/"):
                # The data tree is machine-local and gitignored: a run
                # directory that does not exist yet is not a wrong path.
                continue
            report["missing_paths"].append(f"{rel}: {path}")

        for version in VERSION_RE.findall(text):
            report["contract_versions"].append(f"{rel}: contract version {version}")

    for changed in changed_files(args.changed):
        for stage, areas in STAGE_AREAS.items():
            if changed.startswith(areas):
                doc = DOC_FOR_STAGE[stage]
                if (REPO / doc).exists():
                    report["candidate_documents"].append(f"{changed} -> {doc}")

    if args.json:
        print(json.dumps(report, indent=2))
        return 0

    print("# Mechanical signals for the coherence review\n")
    for key, items in report.items():
        print(f"## {key} ({len(items)})")
        for item in sorted(set(items)):
            print(f"- {item}")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
