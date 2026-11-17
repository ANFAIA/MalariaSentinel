#!/usr/bin/env python3
"""agentic_review_context.py — the material the agentic reviewers read.

The reviewers are language models with read-only access to the tree. What
they get is built here, and built **deterministically**: the same pull
request produces the same context, whatever the model does with it.

The context has five parts:

1. **The pull request's shape** — what changed, classified, and which
   conceptual document covers each changed path.
2. **The diff** — the code and configuration hunks, capped.
3. **The documentation the diff carries** — the comment and docstring
   lines that the change adds or removes.
4. **The mechanical signals** — entities whose code changed and whose
   documentation did not, and prose that states a value by hand which the
   change has made stale. These are **candidates**, not findings: the
   reviewer verifies each one against the code before reporting it.
5. **The documents** — the candidate `.tex` files with their section
   headings, so a reviewer can name the section a change invalidates
   instead of saying "somewhere in the document".

Everything the tool reads is read-only. It writes one file: the context.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import pathlib
import re
import subprocess
import sys

#: The tree the reviewers read. The workflow may point it elsewhere, so
#: that this script can run from a copy taken from the base branch while
#: reading the pull request's tree: the machinery is the base's, the
#: material is the pull request's.
REPO = pathlib.Path(
    os.environ.get(
        "AGENTIC_REVIEW_REPO", pathlib.Path(__file__).resolve().parent.parent
    )
).resolve()

#: Where this script's own helpers are imported from. It is separate from
#: REPO so that the helper can be the base branch's copy while the tree
#: read is the pull request's.
TOOLS = pathlib.Path(
    os.environ.get("AGENTIC_REVIEW_TOOLS", REPO / "tools")
).resolve()
sys.path.insert(0, str(TOOLS))

from coherence_signals import DOC_FOR_STAGE  # noqa: E402

#: Where each stage's code lives. The first matching prefix wins.
STAGE_PREFIXES: list[tuple[str, str]] = [
    ("mal-core/src/mal_core/download/", "download"),
    ("mal-commonlib/src/mal_commonlib/data/loaders/", "download"),
    ("mal-core/src/mal_core/ingest/", "ingest"),
    ("mal-commonlib/src/mal_commonlib/data/", "download"),
    ("mal-core/src/mal_core/scoring/", "scoring"),
    ("mal-core/src/mal_core/training/", "training"),
    ("mal-core/src/mal_core/prediction/", "prediction"),
    ("mal-core/src/mal_core/abm/", "abm"),
    ("mal-core/src/mal_core/habitat/", "abm"),
    ("mal-core/src/mal_core/config/", "abm"),
    ("mal-commonlib/src/mal_commonlib/config/", "abm"),
]

#: The maximum number of diff lines kept per file.
PER_FILE_LINES = 400

#: The maximum number of diff lines kept in total.
TOTAL_LINES = 4000

#: The maximum number of signal rows of one class.
MAX_SIGNALS = 60


# --------------------------------------------------------------------------
# git
# --------------------------------------------------------------------------


def git(*args: str, repo: pathlib.Path = REPO) -> str:
    """Run a git command and return its stdout."""
    proc = subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.stdout


def git_files(base: str, head: str) -> list[str]:
    out = git("diff", "--name-only", f"{base}...{head}")
    return [line for line in out.splitlines() if line.strip()]


def git_show(ref: str, path: str) -> str | None:
    proc = subprocess.run(
        ["git", "show", f"{ref}:{path}"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return None
    return proc.stdout


# --------------------------------------------------------------------------
# classification
# --------------------------------------------------------------------------


def classify(path: str) -> str:
    if path.endswith(".py"):
        return "test" if "/tests/" in path or path.startswith("tests/") else "python"
    if path.endswith((".hpp", ".cpp", ".h", ".cc")):
        return "test" if "/tests/" in path else "cpp"
    if path.endswith((".yaml", ".yml", ".toml", ".json", ".cfg", ".ini")):
        return "config"
    if path.endswith(".tex"):
        return "document"
    if path.endswith(".md"):
        return "prose"
    return "other"


def stage_for(path: str) -> str | None:
    for prefix, stage in STAGE_PREFIXES:
        if path.startswith(prefix):
            return stage
    return None


def candidate_document(path: str) -> str | None:
    stage = stage_for(path)
    if stage is None:
        return None
    return DOC_FOR_STAGE.get(stage)


# --------------------------------------------------------------------------
# the diff
# --------------------------------------------------------------------------


def diff_for(base: str, head: str, paths: list[str]) -> str:
    """The unified diff of the given paths, capped per file and in total."""
    if not paths:
        return ""
    proc = subprocess.run(
        ["git", "diff", "--unified=5", f"{base}...{head}", "--", *paths],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    text = proc.stdout
    blocks: list[str] = []
    total = 0
    current: list[str] = []
    for line in text.splitlines():
        if line.startswith("diff --git "):
            if current:
                blocks.append("\n".join(current))
            current = [line]
        else:
            current.append(line)
    if current:
        blocks.append("\n".join(current))
    kept: list[str] = []
    for block in blocks:
        lines = block.splitlines()
        if len(lines) > PER_FILE_LINES:
            omitted = len(lines) - PER_FILE_LINES
            lines = lines[:PER_FILE_LINES] + [f"... ({omitted} more lines)"]
        if total + len(lines) > TOTAL_LINES:
            kept.append("... (the diff continues; the rest was capped)")
            break
        total += len(lines)
        kept.append("\n".join(lines))
    return "\n".join(kept)


COMMENT_RE = re.compile(r"^\s*(#|//|/\*|\*|\"\"\"|''')")


def comment_lines(diff: str) -> tuple[list[str], list[str]]:
    """The comment lines the diff adds and removes."""
    added: list[str] = []
    removed: list[str] = []
    for line in diff.splitlines():
        if line.startswith("+++") or line.startswith("---"):
            continue
        if line.startswith("+"):
            body = line[1:]
            if COMMENT_RE.match(body):
                added.append(body.rstrip())
        elif line.startswith("-"):
            body = line[1:]
            if COMMENT_RE.match(body):
                removed.append(body.rstrip())
    return added, removed


# --------------------------------------------------------------------------
# signal 1 — an entity whose code changed and whose documentation did not
# --------------------------------------------------------------------------


def _python_entities(source: str) -> dict[str, tuple[str, str | None]]:
    """Every function and class of a Python file: its source and its docstring."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return {}
    found: dict[str, tuple[str, str | None]] = {}

    def walk(node: ast.AST, prefix: str) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                name = f"{prefix}{child.name}"
                segment = ast.get_source_segment(source, child) or ""
                found[name] = (segment, ast.get_docstring(child))
                walk(child, f"{name}.")
            elif isinstance(child, ast.Module):
                walk(child, prefix)

    walk(tree, "")
    return found


def python_doc_signals(base: str, head: str, paths: list[str]) -> list[str]:
    """The Python entities whose code changed without their docstring changing."""
    signals: list[str] = []
    for path in paths:
        if classify(path) != "python":
            continue
        head_source = git_show(head, path)
        base_source = git_show(base, path)
        if head_source is None:
            continue
        head_entities = _python_entities(head_source)
        base_entities = _python_entities(base_source or "")
        for name, (segment, doc) in sorted(head_entities.items()):
            old = base_entities.get(name)
            if old is not None and old[0] == segment:
                continue  # the entity did not change
            if doc is None:
                lines = _line_of(head_source, name)
                signals.append(
                    f"- {path}:{lines} — `{name}` changed and carries no docstring"
                )
            elif old is not None and old[1] == doc:
                lines = _line_of(head_source, name)
                signals.append(
                    f"- {path}:{lines} — `{name}` changed; its docstring is "
                    "byte-identical to the base's"
                )
    return signals[:MAX_SIGNALS]


def _line_of(source: str, name: str) -> int:
    for number, line in enumerate(source.splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith(f"def {name}") or stripped.startswith(f"class {name}"):
            return number
    return 0


CPP_COMMENT_RE = re.compile(r"^\s*(//|/\*|\*)")


def cpp_doc_signals(base: str, head: str, paths: list[str]) -> list[str]:
    """The C++ declarations that changed under a comment that did not."""
    signals: list[str] = []
    for path in paths:
        if classify(path) != "cpp":
            continue
        head_source = git_show(head, path)
        base_source = git_show(base, path) or ""
        if head_source is None:
            continue
        head_lines = head_source.splitlines()
        base_lines = base_source.splitlines()
        changed = _changed_line_numbers(base, head, path)
        for number in sorted(changed):
            if number > len(head_lines):
                continue
            line = head_lines[number - 1]
            if not _is_declaration(line):
                continue
            comment = _comment_above(head_lines, number)
            if not comment:
                signals.append(
                    f"- {path}:{number} — the declaration changed and carries no comment"
                )
                continue
            old_comment = _comment_above(base_lines, number)
            if old_comment == comment:
                signals.append(
                    f"- {path}:{number} — the declaration changed; the comment "
                    "above it is byte-identical to the base's"
                )
    return signals[:MAX_SIGNALS]


def _is_declaration(line: str) -> bool:
    stripped = line.strip()
    if not stripped or stripped.startswith(("#", "//", "*", "/*")):
        return False
    return bool(
        re.match(
            r"^(?:[A-Za-z_][\w:<>,\s\*&\[\]]*?\s)?[A-Za-z_]\w*\s*\([^;]*\)\s*"
            r"(?:const\s*)?(?:noexcept\s*)?(?:override\s*)?(?:=\s*0\s*)?;",
            stripped,
        )
    )


def _comment_above(lines: list[str], number: int) -> str:
    """The comment block directly above a line."""
    collected: list[str] = []
    index = number - 2
    while 0 <= index < len(lines):
        line = lines[index].strip()
        if not line:
            break
        if CPP_COMMENT_RE.match(line) or line.endswith("*/"):
            collected.append(line)
            index -= 1
            continue
        break
    return "\n".join(reversed(collected))


def _changed_line_numbers(base: str, head: str, path: str) -> set[int]:
    """The line numbers in the head that the diff touches."""
    proc = subprocess.run(
        ["git", "diff", "--unified=0", f"{base}...{head}", "--", path],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    numbers: set[int] = set()
    for line in proc.stdout.splitlines():
        match = re.match(r"^@@ -\S+ \+(\d+)(?:,(\d+))? @@", line)
        if not match:
            continue
        start = int(match.group(1))
        count = int(match.group(2) or 1)
        numbers.update(range(start, start + count))
    return numbers


# --------------------------------------------------------------------------
# signal 2 — prose that states a value by hand
# --------------------------------------------------------------------------

MACRO_RE = re.compile(r"\\(mskey|codeconst|code|modelkey)\{")
MACRO_CALL_RE = re.compile(r"\\(mskey|codeconst|code|modelkey)\{[^}]*\}")
LITERAL_RE = re.compile(r"(?<![\w.])(-?\d+\.\d+|-?\d+)(?![\w.])")


def _without_macros(text: str) -> str:
    """The text with the macro calls removed.

    A line may mix a number written by hand with a macro: the number is
    prose and can go stale; the macro is regenerated and cannot.
    """
    return MACRO_CALL_RE.sub(" ", text)


def stale_prose_candidates(base: str, head: str, paths: list[str]) -> list[str]:
    """The numbers the documents write by hand that the change has moved.

    The match is on the **value**, not on the symbol: a document writes
    "0.87" long before it writes the name of the constant it came from,
    and it is the number that goes stale. The generated documents are
    excluded: they are rewritten from the code, so they cannot be stale.
    """
    changed = _changed_literals(base, head, paths)
    if not changed:
        return []
    documents = {
        name: lines
        for name, lines in _documents().items()
        if "/generated/" not in name
    }
    signals: list[str] = []
    for symbol, old, new in changed:
        if not old:
            continue
        for document, lines in documents.items():
            for number, text in enumerate(lines, start=1):
                prose = _without_macros(text)
                if not re.search(rf"(?<![\w.]){re.escape(old)}(?![\w.])", prose):
                    continue
                signals.append(
                    f"- {document}:{number} — the value `{old}` moved "
                    f"({symbol} → {new}) and this line writes `{old}` by hand"
                )
    return signals[:MAX_SIGNALS]


def _changed_literals(
    base: str, head: str, paths: list[str]
) -> list[tuple[str, str, str]]:
    """The constants whose value changed: their name, the old value, the new one."""
    found: list[tuple[str, str, str]] = []
    for path in paths:
        if classify(path) not in {"python", "config"}:
            continue
        proc = subprocess.run(
            ["git", "diff", "--unified=0", f"{base}...{head}", "--", path],
            cwd=REPO,
            capture_output=True,
            text=True,
            check=False,
        )
        old_lines = (git_show(base, path) or "").splitlines()
        new_lines = (git_show(head, path) or "").splitlines()
        old_values = _assignments(old_lines)
        new_values = _assignments(new_lines)
        for name, new in new_values.items():
            old = old_values.get(name)
            if old is None or old == new:
                continue
            found.append((name, old, new))
    return found


def _assignments(lines: list[str]) -> dict[str, str]:
    """The literal assignments of a file: the name and the value as written."""
    values: dict[str, str] = {}
    pattern = re.compile(
        r"^\s*(?:[A-Z_][A-Z0-9_]*\s*=\s*|[\"']?([\w.]+)[\"']?\s*:\s*)"
        r"(?P<value>-?\d+\.\d+|-?\d+)\s*[,;#]?\s*(?:#.*)?$"
    )
    for line in lines:
        match = pattern.match(line)
        if not match:
            continue
        name = match.group(1) or line.split("=", 1)[0].strip()
        values[name] = match.group("value")
    return values


def _documents() -> dict[str, list[str]]:
    documents: dict[str, list[str]] = {}
    for path in sorted((REPO / "docs" / "concepts").rglob("*.tex")):
        rel = str(path.relative_to(REPO))
        if "odd-2010-template" in rel:
            continue
        documents[rel] = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return documents


def document_sections() -> dict[str, list[str]]:
    """The headings of every document, with their line numbers."""
    sections: dict[str, list[str]] = {}
    for rel, lines in _documents().items():
        rows = []
        for number, line in enumerate(lines, start=1):
            match = re.match(r"^\\(?:sub)*section\{(.+?)\}", line)
            if match:
                rows.append(f"  - {rel}:{number} — {match.group(1)}")
        if rows:
            sections[rel] = rows
    return sections


# --------------------------------------------------------------------------
# the context
# --------------------------------------------------------------------------


def build(base: str, head: str) -> str:
    paths = git_files(base, head)
    code_paths = [
        path
        for path in paths
        if classify(path) in {"python", "cpp", "config"}
    ]
    diff = diff_for(base, head, code_paths)
    added, removed = comment_lines(diff)

    counts: dict[str, int] = {}
    for path in paths:
        counts[classify(path)] = counts.get(classify(path), 0) + 1

    out: list[str] = []
    out.append("# The pull request under review")
    out.append("")
    out.append(f"- base: `{base}` ({git('rev-parse', base).strip()[:12]})")
    out.append(f"- head: `{head}` ({git('rev-parse', head).strip()[:12]})")
    out.append(
        "- changed files: "
        + ", ".join(f"{count} {kind}" for kind, count in sorted(counts.items()))
    )
    out.append("")
    out.append("## The changed files")
    out.append("")
    out.append("| file | kind | stage | the document that covers it |")
    out.append("|---|---|---|---|")
    for path in paths:
        stage = stage_for(path)
        document = candidate_document(path)
        out.append(
            f"| `{path}` | {classify(path)} | {stage or '—'} | "
            f"{('`' + document + '`') if document else '—'} |"
        )
    out.append("")

    out.append("## The diff of the code and the configuration")
    out.append("")
    out.append("```diff")
    out.append(diff or "(no code or configuration changed)")
    out.append("```")
    out.append("")

    out.append("## The documentation the diff carries")
    out.append("")
    out.append("### Added")
    out.append("")
    out.extend(f"    {line}" for line in added[:200] or ["(none)"])
    out.append("")
    out.append("### Removed")
    out.append("")
    out.extend(f"    {line}" for line in removed[:200] or ["(none)"])
    out.append("")

    out.append("## Mechanical signals: the code changed, the documentation did not")
    out.append("")
    out.append("These are **candidates**, not findings. Verify each against the code.")
    out.append("")
    signals = python_doc_signals(base, head, paths)
    out.append("### Python")
    out.append("")
    out.extend(signals or ["- (none)"])
    out.append("")
    signals = cpp_doc_signals(base, head, paths)
    out.append("### C++")
    out.append("")
    out.extend(signals or ["- (none)"])
    out.append("")

    out.append("## Mechanical signal: prose that states a value by hand")
    out.append("")
    out.append(
        "A document may write a number as text; when the code moves that "
        "number, the text is stale until it is rewritten. A document that "
        "uses a macro (`\\mskey{}`, `\\codeconst{}`) is regenerated and "
        "needs no edit."
    )
    out.append("")
    signals = stale_prose_candidates(base, head, paths)
    out.extend(signals or ["- (none)"])
    out.append("")

    out.append("## The documents, and their sections")
    out.append("")
    for document, rows in sorted(document_sections().items()):
        out.append(f"### {document}")
        out.append("")
        out.extend(rows)
        out.append("")

    out.append("## The contracts")
    out.append("")
    out.append(_contracts_summary())
    out.append("")
    return "\n".join(out) + "\n"


def _contracts_summary() -> str:
    path = REPO / "docs" / "concepts" / "contracts.yaml"
    if not path.exists():
        return "(no contracts.yaml)"
    artefacts = []
    current: dict | None = None
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("- key:"):
            if current:
                artefacts.append(current)
            current = {"key": stripped.split(":", 1)[1].strip()}
        elif current is not None and stripped and not stripped.startswith("#"):
            if ":" in stripped and not stripped.startswith("-"):
                name, value = stripped.split(":", 1)
                current[name.strip()] = value.strip()
    if current:
        artefacts.append(current)
    rows = [
        "- "
        + ", ".join(
            f"{key}={value}"
            for key, value in artefact.items()
            if key in {"key", "producer", "consumers", "version_from"}
        )
        for artefact in artefacts
    ]
    return "\n".join(rows) or "(none)"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="origin/main")
    parser.add_argument("--head", default="HEAD")
    parser.add_argument("--out", default="-")
    args = parser.parse_args(argv)

    context = build(args.base, args.head)
    if args.out == "-":
        sys.stdout.write(context)
    else:
        pathlib.Path(args.out).write_text(context, encoding="utf-8")
        print(f"wrote {args.out} ({len(context)} characters)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
