#!/usr/bin/env python3
"""merge_agentic_reviews.py — one comment out of three reviewers' reports.

Each reviewer writes a report: prose for a human, then a JSON array of
findings. This tool reads the three reports, merges the arrays, drops
the duplicates, and writes:

* `comment.md` — the comment the workflow posts, with one section per
  reviewer and a single findings table at the end;
* `findings.json` — the merged array, each finding carrying the lens
  that found it, for the measurement that comes later.

A report that is missing, empty, or unparseable is not a failure: it is
recorded as "the reviewer returned nothing" and the merge continues. The
tool never writes a finding that is not in a report.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

FINDINGS_RE = re.compile(r"```json\s*(\[.*?\])\s*```", re.DOTALL)

#: The order the lenses appear in the comment.
LENS_ORDER = ["documentation", "structure", "claims"]

SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}

#: The words that carry no meaning when two titles are compared.
STOP_WORDS = {
    "a", "an", "the", "of", "in", "is", "and", "or", "to", "it", "its",
    "that", "this", "so", "not", "no", "on", "at", "by", "for", "with",
    "but", "has", "have", "had", "was", "were", "be", "been", "being",
    "as", "if", "then", "than", "there", "their", "them", "they", "which",
    "when", "while", "does", "do", "did", "not",
}


def _tokens(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9_]+", text.lower())
    return {word for word in words if word not in STOP_WORDS and len(word) > 2}


def _similarity(left: str, right: str) -> float:
    """The Jaccard similarity of two titles' meaningful words."""
    a, b = _tokens(left), _tokens(right)
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def parse_report(text: str) -> tuple[str, list[dict]]:
    """The prose of a report and its findings."""
    match = FINDINGS_RE.search(text)
    prose = text[: match.start()] if match else text
    findings: list[dict] = []
    if match:
        try:
            parsed = json.loads(match.group(1))
        except json.JSONDecodeError:
            parsed = []
        if isinstance(parsed, list):
            findings = [item for item in parsed if isinstance(item, dict)]
    return prose.strip(), findings


def key_of(finding: dict) -> tuple[str, str, str]:
    return (
        str(finding.get("file", "")).strip(),
        str(finding.get("line", "")).strip(),
        str(finding.get("title", "")).strip().lower(),
    )


#: The maximum number of characters kept from one lens's prose.
PROSE_LIMIT = 1800


def _cap(text: str, limit: int = PROSE_LIMIT) -> str:
    """The prose, cut at a paragraph boundary when it is too long."""
    if len(text) <= limit:
        return text
    cut = text[:limit]
    boundary = cut.rfind("\n\n")
    if boundary > limit * 0.5:
        cut = cut[:boundary]
    return cut.rstrip() + "\n\n_(the rest of the report is in the artefact)_"


def merge(reports: dict[str, str]) -> tuple[str, list[dict]]:
    """The comment and the merged findings."""
    prose_parts: list[str] = []
    collected: list[dict] = []
    seen: set[tuple[str, str, str]] = set()

    for lens in LENS_ORDER + [l for l in reports if l not in LENS_ORDER]:
        if lens not in reports:
            continue
        prose, findings = parse_report(reports[lens])
        title = {
            "documentation": "Is the change documented?",
            "structure": "Does a structural change have its document?",
            "claims": "Does the code do what it claims?",
        }.get(lens, lens)
        prose_parts.append(f"### {title}\n")
        prose_parts.append(_cap(prose) if prose else "_(the reviewer returned nothing)_")
        prose_parts.append("")
        for finding in findings:
            key = key_of(finding)
            if key in seen:
                continue
            seen.add(key)
            collected.append({**finding, "lens": lens, "lenses": [lens]})

    merged = _merge_similar(collected)
    merged.sort(
        key=lambda item: (
            SEVERITY_ORDER.get(str(item.get("severity", "")).lower(), 3),
            str(item.get("file", "")),
            str(item.get("line", "")),
        )
    )
    return "\n".join(prose_parts), merged


def _merge_similar(findings: list[dict]) -> list[dict]:
    """Fold the findings that two lenses reported the same way into one.

    Two lenses that look at one change from different angles often find
    the same defect and word it differently. The comment should say it
    once: the same file, the same line, and titles that share their
    meaningful words are one finding.
    """
    merged: list[dict] = []
    for finding in findings:
        for existing in merged:
            if existing.get("file") != finding.get("file"):
                continue
            if str(existing.get("line")) != str(finding.get("line")):
                continue
            if _similarity(
                str(existing.get("title", "")), str(finding.get("title", ""))
            ) < 0.5:
                continue
            existing["lenses"] = sorted(
                set(existing.get("lenses", [])) | set(finding.get("lenses", []))
            )
            if SEVERITY_ORDER.get(
                str(finding.get("severity", "")).lower(), 3
            ) < SEVERITY_ORDER.get(str(existing.get("severity", "")).lower(), 3):
                existing["severity"] = finding.get("severity")
            for field in ("evidence", "impact"):
                value = finding.get(field)
                if value and value not in str(existing.get(field, "")):
                    existing[field] = f"{existing.get(field, '')} {value}".strip()
            break
        else:
            merged.append(dict(finding))
    return merged


def comment_text(prose: str, findings: list[dict]) -> str:
    """The comment the workflow posts."""
    lines = [
        "<!-- agentic-doc-review -->",
        "## The agentic review",
        "",
        "*This is an advisory review. It does not block the merge, and it "
        "does not require any file to change.*",
        "",
        prose.rstrip(),
        "",
    ]
    if findings:
        lines.append("### The findings")
        lines.append("")
        lines.append("| # | severity | where | what |")
        lines.append("|---|---|---|---|")
        for number, finding in enumerate(findings, start=1):
            where = f"`{finding.get('file', '')}`"
            if finding.get("line"):
                where += f":{finding['line']}"
            title = str(finding.get("title", "")).replace("|", "/")
            lines.append(
                f"| {number} | {finding.get('severity', '—')} | {where} | {title} |"
            )
        lines.append("")
        for number, finding in enumerate(findings, start=1):
            lines.append(f"**{number}. {finding.get('title', '')}**")
            lines.append("")
            if finding.get("evidence"):
                lines.append(f"- Evidence: {finding['evidence']}")
            if finding.get("impact"):
                lines.append(f"- Impact: {finding['impact']}")
            lines.append("")
    else:
        lines.append("### The findings")
        lines.append("")
        lines.append("_None. The three reviewers found nothing they could prove._")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--report",
        action="append",
        default=[],
        metavar="LENS=PATH",
        help="a report to merge; repeat it for each lens",
    )
    parser.add_argument("--out-comment", default="-")
    parser.add_argument("--out-findings", default="-")
    args = parser.parse_args(argv)

    reports: dict[str, str] = {}
    for item in args.report:
        lens, _, path = item.partition("=")
        if not path:
            lens, path = LENS_ORDER[len(reports) % len(LENS_ORDER)], lens
        file = pathlib.Path(path)
        reports[lens] = file.read_text(encoding="utf-8") if file.exists() else ""

    prose, findings = merge(reports)
    text = comment_text(prose, findings)

    if args.out_comment == "-":
        sys.stdout.write(text)
    else:
        pathlib.Path(args.out_comment).write_text(text, encoding="utf-8")
    payload = json.dumps(findings, indent=2, ensure_ascii=False) + "\n"
    if args.out_findings == "-":
        sys.stdout.write(payload)
    else:
        pathlib.Path(args.out_findings).write_text(payload, encoding="utf-8")
    print(f"merged {len(findings)} finding(s) from {len(reports)} report(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
