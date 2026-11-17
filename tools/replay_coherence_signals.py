#!/usr/bin/env python3
"""Replay the mechanical signals over a branch's document-touching commits.

The measurement the plan asks for is the false-positive rate of the
coherence review over the merges that carry the conceptual documents. That
population is empty today (the documents have never been on ``main``), so
this script measures the population that DOES exist: the commits of a branch
that touch ``docs/concepts/``.

For every such commit it

1. materialises the tree with ``git archive <sha>`` into a temporary
   directory,
2. runs the signal tool INSIDE that tree with ``--changed`` set to the
   files the commit changed (the tool resolves its repository root from
   ``__file__`` and shells out to git, so it must run in the archived tree),
3. records the findings, per class and per commit.

Two tools can be replayed:

* ``--tool tree`` — the tool the commit itself carried. A commit before the
  tool existed yields NO population: it is not a rate of zero, it is a
  commit the measurement cannot speak about.
* ``--tool current`` — the tool in the working tree, copied into the
  archived tree. This is the only way to replay the checks that the branch
  does not carry yet.

Usage:
    uv run --package mal-core python tools/replay_coherence_signals.py \
        [--base main] [--head HEAD] [--tool tree|current] [--json OUT.json]
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TOOL = REPO / "tools" / "coherence_signals.py"
DOCUMENT_GLOB = "docs/concepts/"


def git(*args: str, cwd: Path = REPO) -> str:
    result = subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=False
    )
    return result.stdout


def base_commit(base: str, head: str) -> str:
    out = git("merge-base", base, head).strip()
    return out or base


def document_commits(base: str, head: str) -> list[str]:
    """The commits between ``base`` and ``head`` that touch the documents."""
    out = git(
        "log", "--reverse", "--format=%H", f"{base}..{head}", "--", DOCUMENT_GLOB
    )
    return [line.strip() for line in out.splitlines() if line.strip()]


def changed_files(sha: str) -> list[str]:
    out = git(
        "diff-tree", "--no-commit-id", "--name-only", "-r", "--root", sha
    )
    return [line.strip() for line in out.splitlines() if line.strip()]


def subject(sha: str) -> str:
    return git("log", "-1", "--format=%s", sha).strip()


def replay(sha: str, tool: str, workdir: Path) -> dict | None:
    """Run the signal tool against the tree of ``sha``.

    Returns None when the commit's tree has no tool at all: that is an
    empty population, not a measurement.
    """
    tree = workdir / sha
    tree.mkdir(parents=True, exist_ok=True)
    archive = subprocess.run(
        ["git", "archive", sha], cwd=REPO, capture_output=True, check=False
    )
    if archive.returncode != 0:
        return {"error": "git archive failed", "sha": sha}
    tar = subprocess.run(
        ["tar", "-x", "-C", str(tree)], input=archive.stdout, check=False
    )
    if tar.returncode != 0:
        return {"error": "tar failed", "sha": sha}
    target = tree / "tools" / "coherence_signals.py"
    if not target.exists():
        return None
    if tool == "current":
        shutil.copyfile(TOOL, target)
    files = changed_files(sha)
    result = subprocess.run(
        [sys.executable, str(target), "--changed", *files, "--json"],
        cwd=tree,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return {"error": result.stderr[-2000:], "sha": sha}
    try:
        report = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        return {"error": f"unparseable output: {exc}", "sha": sha}
    counts = {key: len(items) for key, items in report.items() if items}
    return {
        "sha": sha,
        "subject": subject(sha),
        "changed": files,
        "counts": counts,
        "findings": {
            key: items for key, items in report.items() if items
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="main")
    parser.add_argument("--head", default="HEAD")
    parser.add_argument("--tool", choices=("tree", "current"), default="current")
    parser.add_argument("--json", default="")
    args = parser.parse_args()

    base = base_commit(args.base, args.head)
    commits = document_commits(base, args.head)
    print(
        f"# replay over {len(commits)} document-touching commits "
        f"({base}..{args.head}), tool={args.tool}",
        file=sys.stderr,
    )

    results = []
    empty: list[str] = []
    with tempfile.TemporaryDirectory(prefix="coherence-replay-") as tmp:
        workdir = Path(tmp)
        for sha in commits:
            outcome = replay(sha, args.tool, workdir)
            if outcome is None:
                empty.append(sha)
                print(f"{sha}  (no tool in this tree: empty population)")
                continue
            results.append(outcome)
            print(f"{sha}  {outcome.get('subject', '')}")
            for key, count in sorted(outcome.get("counts", {}).items()):
                print(f"    {key}: {count}")

    per_class: dict[str, int] = {}
    for outcome in results:
        for key, count in outcome.get("counts", {}).items():
            per_class[key] = per_class.get(key, 0) + count

    print("\n## totals per class")
    for key, count in sorted(per_class.items()):
        print(f"- {key}: {count}")
    print(f"\ncommits measured: {len(results)}")
    print(f"commits with an empty population (no tool in the tree): {len(empty)}")
    for sha in empty:
        print(f"  - {sha} {subject(sha)}")

    if args.json:
        Path(args.json).write_text(
            json.dumps(
                {
                    "base": base,
                    "head": args.head,
                    "tool": args.tool,
                    "commits": results,
                    "empty_population": empty,
                    "per_class_totals": per_class,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        print(f"\nwrote {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
