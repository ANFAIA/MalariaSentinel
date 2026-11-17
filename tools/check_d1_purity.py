#!/usr/bin/env python3
"""Report the numbers a conceptual document still types by hand.

The project's rule **D1** says no value is written by hand: a number the
code owns comes from a generated macro (`\\mskey{...}` for the model
constants, `\\codeconst{...}` for the values that live in the code), and a
number the document owns — a count it enumerates, a unit conversion it
shows, a literature value — is the document's own.

This script finds the numbers that are neither: it strips the generated
macros, the citations and the markup from a document, collects what is
left, and compares it with the values the generator emitted. What remains is
reported with its line, so a reviewer can decide whether it is a genuine
violation or a legitimate literal.

It is a **signal, not a gate**: like the coherence reviewer's signals, a
report here can be wrong, and the rule is that a signal the author cannot
act on is noise.

Usage:
    uv run python tools/check_d1_purity.py [--json] [document ...]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CONCEPTS = REPO / "docs" / "concepts"
GENERATED = CONCEPTS / "generated"

# A numeric literal in the running text.
NUMBER_RE = re.compile(r"(?<![\w.])[-+]?\d+(?:\.\d+)?(?![\w])")

# Constructs whose contents are not prose: generated macros, code spans,
# source citations, labels, references, and the LaTeX preamble's own
# typography. Everything inside them is excluded from the search.
SPANS = (
    re.compile(r"\\mskey\{(?:[^{}]|\{[^{}]*\})*\}"),
    re.compile(r"\\codeconst\{(?:[^{}]|\{[^{}]*\})*\}"),
    re.compile(r"\\code(?:x|b)?\{(?:[^{}]|\{[^{}]*\})*\}"),
    re.compile(r"\\src\{(?:[^{}]|\{[^{}]*\})*\}"),
    re.compile(r"\\label\{[^}]*\}"),
    re.compile(r"\\ref\{[^}]*\}"),
    re.compile(r"\\pageref\{[^}]*\}"),
    re.compile(r"\\input\{[^}]*\}"),
    re.compile(r"\\usepackage(?:\[[^\]]*\])?\{[^}]*\}"),
    re.compile(r"\\documentclass(?:\[[^\]]*\])?\{[^}]*\}"),
    # The sectioning commands and the numbers in their titles: a section
    # number is the document's own numbering, not a value.
    re.compile(r"\\(?:sub)*section\*?\{(?:[^{}]|\{[^{}]*\})*\}"),
    re.compile(r"\\(?:chapter|part|appendix)\*?\{[^}]*\}"),
)

# A year, and the singletons 0 and 1, are almost always the document's own
# (a date, a boolean, a domain bound) and are reported neither as violations
# nor as noise.
BORING = re.compile(r"^(?:0|1)$")

# Lines that are LaTeX machinery rather than prose: the preamble, the
# macro definitions, and the commands that take a numeric argument.
PREAMBLE_END = re.compile(r"\\begin\{document\}")


def documents() -> list[Path]:
    if not CONCEPTS.is_dir():
        return []
    return sorted(
        p
        for p in CONCEPTS.glob("*/*.tex")
        if p.name != "odd-2010-template.tex" and p.parent.name != "generated"
    )


def generated_values() -> set[str]:
    """Every value the generator emitted, as it appears in the documents."""
    values: set[str] = set()
    if not GENERATED.is_dir():
        return values
    for path in GENERATED.glob("*.tex"):
        text = path.read_text(encoding="utf-8")
        # \expandafter\def\csname cc@k@name\endcsname{value}
        for match in re.finditer(
            r"\\expandafter\\def\\csname [^{]+\\endcsname\{([^}]*)\}", text
        ):
            values.add(match.group(1).strip())
        # Table rows: \code{name} & value \\
        for match in re.finditer(r"&\s*([^&\\\n]+?)\s*\\\\", text):
            values.add(match.group(1).strip())
    return values


def strip_spans(text: str) -> str:
    for pattern in SPANS:
        text = pattern.sub(" ", text)
    return text


def candidates(path: Path, known: set[str]) -> list[str]:
    text = path.read_text(encoding="utf-8")
    # Comments: a commented-out number is not a number the document states.
    text = re.sub(r"(?<!\\)%.*", "", text)
    body = PREAMBLE_END.search(text)
    if body:
        text = text[body.end() :]
    text = strip_spans(text)
    out: list[str] = []
    for number, line in enumerate(text.splitlines(), start=1):
        for match in NUMBER_RE.finditer(line):
            value = match.group(0)
            if value in known:
                continue
            if BORING.match(value):
                continue
            if len(value) == 4 and value.isdigit() and 1900 <= int(value) <= 2100:
                continue
            out.append(f"{path.relative_to(REPO)}:{number}: {value} — {line.strip()[:110]}")
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("documents", nargs="*", help="documents to check")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    known = generated_values()
    docs = [Path(d) if Path(d).is_absolute() else REPO / d for d in args.documents]
    if not docs:
        docs = documents()

    report: dict[str, list[str]] = {}
    for doc in docs:
        if not doc.exists():
            print(f"check_d1_purity: no such document: {doc}", file=sys.stderr)
            return 2
        found = candidates(doc, known)
        if found:
            report[str(doc.relative_to(REPO))] = found

    if args.json:
        print(json.dumps(report, indent=2))
        return 0

    print("# Numbers that are not generated\n")
    if not report:
        print("None: every number in the documents is emitted by the generator.")
        return 0
    for name, items in report.items():
        print(f"## {name} ({len(items)})")
        for item in items:
            print(f"- {item}")
        print()
    print(
        "These are candidates, not violations: a count the document enumerates,\n"
        "a unit conversion, a literature value or an example is legitimate.\n"
        "The signal is only worth acting on when the number is a value the code\n"
        "owns."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
