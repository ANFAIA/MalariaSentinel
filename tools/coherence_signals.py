#!/usr/bin/env python3
"""Mechanical signals for the warnings-only coherence review.

The coherence review (``.github/workflows/coherence-review.yml``) is an
ADVISOR: it reports incoherences between the conceptual documents and the
implementation, and it never blocks. This script produces the mechanical
signals the reviewer may cite — it does not decide anything, and a signal
here is not a verdict. It always exits 0: a signal that cannot be computed
is reported as a gap, never as a failure.

Signals
-------
1. ``\\mskey{...}`` in a document vs the keys the model constants have: a
   key the configuration no longer has.
2. ``\\codeconst{...}`` in a document vs the keys the generator emitted: a
   code constant the code no longer has.
3. ``\\code{...}`` identifiers vs the symbols that exist in the tree: a
   name the document mentions that nothing defines.
4. Paths named in a document (``docs/...``, ``papers/...``, ``scripts/...``,
   ``mal-*/...``) vs the tree: a path that no longer exists.
5. Contract versions mentioned in a document, ADJUDICATED: the version the
   document states vs the version the code has (the model constants, the
   prediction stage's own literal) — and vs the versions declared in
   ``docs/concepts/contracts.yaml``.
6. The state sidecar's keys: the keys the document lists vs the keys
   ``write_state_sidecar`` writes, and the keys ``contracts.yaml`` declares
   vs the same.
7. Cardinalities stated in prose ("the thirteen composite dimensions",
   "fifteen keys") vs the counts the code has.
8. Changed paths vs the stage documents that cover them: the candidate
   documents a reviewer should read.
9. Citations of the form ``file.py:42`` vs the files: a citation that
   points past the end of the file it names.

The checks REUSE the project's own readers: the value generator
(``tools/gen_concepts_values.py``) is imported as a module, so the state
bands, the sidecar keys, the model constants and the code constants are
read the way the documentation build reads them. A forked reader drifts.

Usage:
    uv run --package mal-core python tools/coherence_signals.py \
        [--changed FILE ...] [--json]
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
CONCEPTS = REPO / "docs" / "concepts"
GENERATOR = REPO / "tools" / "gen_concepts_values.py"
SCORERS = REPO / "mal-core" / "src" / "mal_core" / "scoring" / "scorers"
REGISTRY = REPO / "mal-core" / "src" / "mal_core" / "scoring" / "registry.py"
GATES = SCORERS / "gates.py"
PREDICTION = REPO / "mal-core" / "src" / "mal_core" / "prediction"
OUTPUT_CONTRACT = (
    REPO / "mal-core" / "src" / "mal_core" / "abm" / "src" / "output_contract.cpp"
)

MSKEY_RE = re.compile(r"\\mskey\{([^}]+)\}")
CODE_RE = re.compile(r"\\code\{([^}]+)\}")
CODE_CONST_RE = re.compile(r"\\codeconst\{([^}]+)\}")
PATH_RE = re.compile(
    r"\b((?:docs|papers|scripts|tools|mal-[a-z\-]+|data)/[A-Za-z0-9_\\\-\./]*[A-Za-z0-9_\-])"
)
VERSION_RE = re.compile(r"contract[^.\n]{0,40}?([0-9]+\.[0-9]+(?:\.[0-9]+)?)")
CITE_RE = re.compile(
    r"([A-Za-z0-9_./\-]*[A-Za-z0-9_\-]\.(?:py|hpp|cpp|cc|c|h|yaml|yml|md|json|txt|tex|sh|html|toml|cfg|ini))"
    r":(\d+)(?:\s*[-–]\s*(\d+))?"
)

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


VERBATIM_RE = re.compile(
    r"\\begin\{(verbatim|lstlisting)\}.*?\\end\{\1\}", re.DOTALL
)

# A macro key is a dotted identifier. A document that writes the macro
# itself (a template, an example) writes something else, and that is
# prose, not a key.
MODEL_KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z0-9_]+)*$")
CODE_KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*\.[A-Za-z0-9_]+$")


def strip_verbatim(text: str) -> str:
    """Drop the literal blocks: their content is pseudocode, not markup."""
    return VERBATIM_RE.sub("", text)


def documents() -> list[Path]:
    if not CONCEPTS.is_dir():
        return []
    return sorted(
        p
        for p in CONCEPTS.glob("*/*")
        if p.suffix in {".tex", ".md"}
        and p.name not in {"odd-2010-template.tex"}
        and p.parent.name != "generated"
    )


# ---------------------------------------------------------------------------
# The generator, imported as a module.
#
# The generator already knows how to read the state bands, the sidecar
# keys, the model constants and the code constants. Re-implementing those
# readers here would create a second source of truth that drifts silently.
# ---------------------------------------------------------------------------


def _load_generator() -> Any | None:
    """Import ``tools/gen_concepts_values.py`` as a module, or None.

    The generator needs the project's own packages on the path (it reads
    the model constants through the validated loader). When they are not
    importable, the generator is None and the checks that need it report a
    gap instead of guessing.
    """
    if not GENERATOR.exists():
        return None
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "gen_concepts_values", GENERATOR
        )
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        sys.modules["gen_concepts_values"] = module
        spec.loader.exec_module(module)
        return module
    except (Exception, SystemExit):
        # The generator reports a missing source file with SystemExit; the
        # signals must survive it (they are an advisor, never a failure).
        return None


def model_values(gen: Any | None) -> dict[str, Any]:
    """The validated model constants, as dotted paths.

    Read through the project's own loader (``load_config``), never by
    re-parsing the YAML: the loader validates the file first, so a
    malformed configuration is a loud failure, not a silent misreading.
    """
    if gen is None:
        return {}
    try:
        return gen.flatten(dict(gen.load_config()))
    except (Exception, SystemExit):
        return {}


def known_macro_keys() -> set[str]:
    """The model-constant keys the generated macros carry (a fallback)."""
    macros = CONCEPTS / "generated" / "macros.tex"
    if not macros.exists():
        return set()
    text = macros.read_text(encoding="utf-8")
    return set(re.findall(r"\\csname ms@k@([^\\]+)\\endcsname", text))


def known_model_keys(values: dict[str, Any], gen: Any | None) -> set[str]:
    """Every model-constant key a document may cite."""
    keys = set(values) | known_macro_keys()
    if gen is not None:
        try:
            keys |= set(gen.flatten(dict(gen.load_config())))
        except (Exception, SystemExit):
            # The generator could not be read: the macros already loaded
            # are the fallback.
            pass
    return keys


def known_code_constants(gen: Any | None) -> set[str]:
    """Every code-constant key a document may cite (``\\codeconst{...}``)."""
    if gen is not None:
        try:
            return set(gen.build_code_values())
        except (Exception, SystemExit):
            # The generator could not be read: the generated fragment is
            # the fallback.
            pass
    macros = CONCEPTS / "generated" / "code-macros.tex"
    if not macros.exists():
        return set()
    text = macros.read_text(encoding="utf-8")
    return set(re.findall(r"\\csname cc@k@([^\\]+)\\endcsname", text))


def code_sidecar_keys(gen: Any | None) -> list[str]:
    """The keys ``write_state_sidecar`` writes, in emission order."""
    if gen is not None:
        try:
            return list(gen.cpp_sidecar_keys())
        except (Exception, SystemExit):
            # The generator could not be read: the writer's own source is
            # the fallback.
            pass
    if not OUTPUT_CONTRACT.exists():
        return []
    text = OUTPUT_CONTRACT.read_text(encoding="utf-8")
    return re.findall(r'j\["([^"]+)"\]\s*=', text)


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


INTRODUCES_RE = re.compile(r"stands for|denotes|means|names the", re.IGNORECASE)


def _introduced_here(text: str, raw_token: str) -> bool:
    """Whether the document itself introduces the symbol.

    A document may name a placeholder of its own ("PAD\\_MULTIPLE stands
    for the wrapper's padding multiple") that the code never defines.
    That is the document's own vocabulary, not an incoherence, so the
    signal skips it.
    """
    for sentence in re.split(r"(?<=[.\n])\s+", text):
        if raw_token in sentence and INTRODUCES_RE.search(sentence):
            return True
    return False


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


def _ignored(rel: Path) -> bool:
    return bool(
        set(rel.parts)
        & {".git", ".venv", ".cache", ".gitagent", "node_modules", "runs"}
    )


def _basename_index() -> dict[str, list[Path]]:
    """Every file in the tree, indexed by its basename."""
    index: dict[str, list[Path]] = {}
    for path in REPO.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(REPO)
        if _ignored(rel):
            continue
        index.setdefault(path.name, []).append(path)
    return index


def _resolve_citation(
    cited: str, index: dict[str, list[Path]]
) -> Path | None:
    """Resolve a cited path to a file, or None when it cannot be decided.

    A document writes ``runner.py:120`` for a file it has already named in
    full. The short form is resolved by the basename, and only when the
    basename is unique in the tree: an ambiguous name is not resolved,
    because a signal that guesses is a signal that cries wolf.
    """
    cited = cited.lstrip("./")
    direct = REPO / cited
    if direct.is_file():
        return direct
    base = cited.rsplit("/", 1)[-1]
    candidates = index.get(base, [])
    if len(candidates) == 1:
        return candidates[0]
    if len(candidates) > 1:
        tail = cited.split("/")[-2] if "/" in cited else ""
        narrowed = [c for c in candidates if tail and tail in c.parts]
        if len(narrowed) == 1:
            return narrowed[0]
    return None


def _file_length(path: Path) -> int:
    try:
        with path.open(encoding="utf-8", errors="replace") as handle:
            return sum(1 for _ in handle)
    except OSError:
        return 0


def citation_report(docs: list[Path]) -> list[str]:
    """Citations that point past the end of the file they name."""
    index = _basename_index()
    out: list[str] = []
    for doc in docs:
        text = doc.read_text(encoding="utf-8")
        text = re.sub(r"\\allowbreak(\{\})?[ \t]*\n[ \t]*", "", text)
        text = _unescape(text)
        rel = doc.relative_to(REPO)
        for cited, first, last in CITE_RE.findall(text):
            target = _resolve_citation(cited, index)
            if target is None:
                continue
            length = _file_length(target)
            high = int(last) if last else int(first)
            if high > length:
                out.append(
                    f"{rel}: {cited}:{first}"
                    + (f"-{last}" if last else "")
                    + f" (the file has {length} lines)"
                )
    return out


# ---------------------------------------------------------------------------
# Contract versions: adjudicated, not merely collected.
# ---------------------------------------------------------------------------

# Which contract a mention is about. The keyword that occurs LAST before
# the version wins: "State contract 4.0; env-NC contract 3.0" says two
# different things, and the nearest keyword is the one that binds.
CONTRACT_SUBJECTS: dict[str, tuple[str, ...]] = {
    "state": ("state",),
    "env": ("env", "netcdf"),
    "prediction": ("prediction", "predictor"),
}


def contract_versions_in_code(values: dict[str, Any]) -> dict[str, set[str]]:
    """The contract versions the CODE states, by subject."""
    versions: dict[str, set[str]] = {
        "state": set(),
        "env": set(),
        "prediction": set(),
    }
    if values.get("contracts.cogs_state"):
        versions["state"].add(str(values["contracts.cogs_state"]))
    if values.get("contracts.env_nc"):
        versions["env"].add(str(values["contracts.env_nc"]))
    if PREDICTION.is_dir():
        for path in sorted(PREDICTION.glob("*.py")):
            try:
                text = path.read_text(encoding="utf-8")
            except OSError:
                continue
            for value in re.findall(
                r"contract_version[\"']?\s*[:=]\s*[\"']([0-9]+\.[0-9]+)", text
            ):
                versions["prediction"].add(value)
    return versions


def _subject_of(text: str, position: int) -> str | None:
    """The contract a version mention is about, by the nearest keyword."""
    window = text[max(0, position - 120) : position].lower()
    best: tuple[int, str] | None = None
    for subject, keywords in CONTRACT_SUBJECTS.items():
        for keyword in keywords:
            for match in re.finditer(rf"\b{re.escape(keyword)}\b", window):
                if best is None or match.end() > best[0]:
                    best = (match.end(), subject)
    return best[1] if best else None


def contract_version_report(
    docs: list[Path], values: dict[str, Any]
) -> tuple[list[str], list[str]]:
    """The version mentions, and the ones the code contradicts.

    Returns ``(mentions, errors)``. A mention is adjudicated against the
    version the code has for the contract it names; a mention whose
    subject cannot be decided is only an error when its version matches
    no contract in the code at all.
    """
    versions = contract_versions_in_code(values)
    known = {v for values_ in versions.values() for v in values_}
    mentions: list[str] = []
    errors: list[str] = []
    for doc in docs:
        text = strip_verbatim(doc.read_text(encoding="utf-8"))
        rel = doc.relative_to(REPO)
        for match in VERSION_RE.finditer(text):
            version = match.group(1)
            mentions.append(f"{rel}: contract version {version}")
            subject = _subject_of(text, match.start(1))
            expected = versions.get(subject or "", set())
            if subject and len(expected) == 1:
                have = next(iter(expected))
                if version != have:
                    errors.append(
                        f"{rel}: contract version {version} (the {subject} "
                        f"contract) — the code has {have}"
                    )
            elif not subject and known and version not in known:
                errors.append(
                    f"{rel}: contract version {version} — no contract in the "
                    "code has that version"
                )
    return mentions, errors


def contracts_yaml(gen: Any | None) -> dict[str, Any]:
    """The contracts file, read through the generator's own reader."""
    if gen is not None:
        try:
            return gen.read_contracts_yaml()
        except (Exception, SystemExit):
            return {}
    return {}


def contract_file_report(
    gen: Any | None, values: dict[str, Any]
) -> list[str]:
    """The generator's own cross-check of ``contracts.yaml`` vs the code.

    The generator fails the documentation build on a mismatch; here the
    same check is a signal, so a mismatch is visible before the build.
    """
    if gen is None:
        return []
    try:
        contracts = gen.read_contracts_yaml()
        bands = gen.cpp_band_names()
        problems = gen.cross_check_contracts(contracts, values, bands)
    except (Exception, SystemExit) as exc:
        return [f"docs/concepts/contracts.yaml: the cross-check did not run ({exc})"]
    return [f"docs/concepts/contracts.yaml: {problem}" for problem in problems]


# Which contract an artefact is about, so a declaration can be compared
# with the version the code has for that contract.
ARTEFACT_SUBJECT = {
    "state_cog": "state",
    "state_sidecar": "state",
    "env": "env",
    "habitat": "env",
}


def contract_declaration_report(
    contracts: dict[str, Any], values: dict[str, Any], gen: Any | None
) -> list[str]:
    """The contracts file's declarations against the code.

    Every declaration is compared with the code that has to match it:

    * the declared version against the contract the artefact belongs to;
    * the declared sidecar keys against the keys the writer emits, in
      order (the order is part of the contract);
    * the declared band names against ``STATE_BAND_NAMES`` in wire.hpp;
    * the declared nodata against ``ingest.nodata_sentinel``.

    The code is read through the generator's readers
    (``cpp_sidecar_keys``, ``cpp_band_names``), never by a second copy of
    them.
    """
    out: list[str] = []
    code_sidecar = list(code_sidecar_keys(gen))
    code_bands = list(gen.cpp_band_names()) if gen is not None else []
    nodata = values.get("ingest.nodata_sentinel")
    for artefact in contracts.get("artefacts", []) or []:
        key = artefact.get("key")
        subject = ARTEFACT_SUBJECT.get(str(key))
        version_from = artefact.get("version_from")
        declared_version = artefact.get("version")
        if version_from:
            resolved = values.get(version_from)
            if resolved is None:
                out.append(
                    f"docs/concepts/contracts.yaml: {key} declares "
                    f"version_from {version_from!r}, which is not a model "
                    "constant"
                )
            elif declared_version and str(declared_version) != str(resolved):
                out.append(
                    f"docs/concepts/contracts.yaml: {key} declares version "
                    f"{declared_version} but {version_from} is {resolved}"
                )
            if subject and resolved is not None:
                code_version = values.get(
                    "contracts.cogs_state"
                    if subject == "state"
                    else "contracts.env_nc"
                )
                if code_version is not None and str(resolved) != str(code_version):
                    out.append(
                        f"docs/concepts/contracts.yaml: {key} resolves to "
                        f"{resolved} but the {subject} contract is "
                        f"{code_version}"
                    )
        keys = artefact.get("keys")
        if keys is not None:
            declared = [str(k) for k in keys]
            if code_sidecar and declared != code_sidecar:
                missing = sorted(set(code_sidecar) - set(declared))
                extra = sorted(set(declared) - set(code_sidecar))
                if missing:
                    out.append(
                        f"docs/concepts/contracts.yaml: {key} omits "
                        f"{len(missing)} key(s) the writer emits: "
                        f"{', '.join(missing)}"
                    )
                if extra:
                    out.append(
                        f"docs/concepts/contracts.yaml: {key} declares "
                        f"key(s) the writer does not emit: {', '.join(extra)}"
                    )
                if not missing and not extra:
                    out.append(
                        f"docs/concepts/contracts.yaml: {key} declares the "
                        "same keys in a different order — the order is part "
                        "of the contract"
                    )
        band_names = artefact.get("band_names")
        if band_names is not None and code_bands:
            declared = [str(b) for b in band_names]
            if declared != code_bands:
                out.append(
                    f"docs/concepts/contracts.yaml: {key} declares band names "
                    f"{declared} — wire.hpp has {code_bands}"
                )
        declared_nodata = artefact.get("nodata")
        if declared_nodata is not None and nodata is not None:
            try:
                equal = float(declared_nodata) == float(nodata)
            except (TypeError, ValueError):
                equal = False
            if not equal:
                out.append(
                    f"docs/concepts/contracts.yaml: {key} declares nodata "
                    f"{declared_nodata} — ingest.nodata_sentinel is {nodata}"
                )
    return out


def declared_sidecar_keys(contracts: dict[str, Any]) -> list[str]:
    """The sidecar keys ``contracts.yaml`` declares (possibly none)."""
    for artefact in contracts.get("artefacts", []) or []:
        if artefact.get("key") == "state_sidecar":
            keys = artefact.get("keys") or artefact.get("sidecar_keys") or []
            return [str(k) for k in keys]
    return []


def sidecar_key_report(
    docs: list[Path], code_keys: list[str], declared: list[str], tree: str
) -> list[str]:
    """The sidecar's keys: the document's list against the writer's.

    A token that names a code symbol rather than a key (the writer's own
    name, for instance) is not a key and is not an error.
    """
    out: list[str] = []
    code_set = set(code_keys)
    for doc in docs:
        text = strip_verbatim(doc.read_text(encoding="utf-8"))
        rel = doc.relative_to(REPO)
        for match in re.finditer(r"State sidecar", text):
            tail = text[match.start() :]
            end = tail.find(r"\item")
            block = tail[:end] if end != -1 else tail
            tokens = {
                _unescape(token)
                for token in re.findall(r"\\code\{([^}]*)\}", block)
            }
            keys = {
                token
                for token in tokens
                if re.fullmatch(r"[a-z][a-z0-9_]*", token)
                and (token in code_set or not _mentioned_in_tree(token, tree))
            }
            missing = sorted(code_set - keys)
            extra = sorted(
                token for token in keys if token not in code_set
            )
            if missing:
                out.append(
                    f"{rel}: the state sidecar's list omits {len(missing)} key(s) "
                    f"the writer emits: {', '.join(missing)}"
                )
            if extra:
                out.append(
                    f"{rel}: the state sidecar's list names key(s) the writer "
                    f"does not emit: {', '.join(extra)}"
                )
    if not declared:
        out.append(
            "docs/concepts/contracts.yaml: the state_sidecar artefact "
            f"declares no keys — the writer emits {len(code_keys)}"
        )
    return out


# ---------------------------------------------------------------------------
# Cardinalities stated in prose.
# ---------------------------------------------------------------------------

NUMBER_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
    "twenty": 20,
}

PROSE_CLAIMS: tuple[dict[str, Any], ...] = (
    {
        "name": "manual_scorers",
        "pattern": re.compile(r"(\w+) scorers carry the flag"),
        "facts": ("manual_scorers",),
    },
    {
        "name": "heaviest_dimensions",
        "pattern": re.compile(r"[Tt]he (\w+) heaviest dimensions"),
        "facts": ("heaviest_ties",),
    },
    {
        "name": "composite_dimensions",
        "pattern": re.compile(r"[Tt]he (\w+) composite dimensions"),
        "facts": ("composite_count",),
    },
    {
        "name": "gates",
        "pattern": re.compile(r"[Tt]he (\w+) gates"),
        "facts": ("gate_count",),
    },
    {
        "name": "hard_floor_declared",
        "pattern": re.compile(r"declared by (\w+) of the composite dimensions"),
        "facts": ("hard_floor_declared",),
    },
    {
        "name": "hard_floor_table",
        "pattern": re.compile(r"\} & (\w+) composite dimensions"),
        "facts": ("hard_floor_declared",),
    },
    {
        "name": "aoi_generalizable",
        "pattern": re.compile(r"\} & (\w+) of the (\w+) gates"),
        "facts": ("aoi_generalizable_gates", "gate_count"),
    },
    {
        "name": "registry_anchors",
        "pattern": re.compile(r"for (\w+) of the (\w+) dimensions only"),
        "facts": ("registry_anchors", "composite_count"),
    },
    {
        "name": "one_weight_family",
        "pattern": re.compile(r"one-weight family is the set of (.+?) dimensions"),
        "facts": ("weight_one_count",),
        "enumeration": True,
    },
    {
        "name": "sidecar_key_count",
        "pattern": re.compile(r"State sidecar\} \(JSON\): (\w+) keys"),
        "facts": ("sidecar_key_count",),
    },
)


def _generated_scoring_table() -> tuple[list[tuple[str, float]], list[str]]:
    """The composite rows and the gate rows of the generated table.

    The table is generated from the registry, so it is the registry's
    own view of the scoring system — the same one the document cites.
    """
    path = CONCEPTS / "generated" / "params-scoring.tex"
    if not path.exists():
        return [], []
    text = path.read_text(encoding="utf-8")
    composite_text, _, gate_text = text.partition("\\paragraph{Gates")
    dims: list[tuple[str, float]] = []
    for line in composite_text.splitlines():
        match = re.match(r"\\code\{([^}]+)\} & ([0-9.]+) & ", line)
        if match:
            dims.append((match.group(1), float(match.group(2))))
    gates: list[str] = []
    for line in gate_text.splitlines():
        match = re.match(r"\\code\{([^}]+)\} & ", line)
        if match:
            gates.append(match.group(1))
    return dims, gates


def scoring_facts(gen: Any | None) -> dict[str, int]:
    """The counts the scoring prose states, taken from the code."""
    facts: dict[str, int] = {}
    dims, gates = _generated_scoring_table()
    if dims:
        facts["composite_count"] = len(dims)
        top = max(weight for _, weight in dims)
        facts["heaviest_ties"] = sum(1 for _, w in dims if w == top)
        facts["weight_one_count"] = sum(1 for _, w in dims if w == 1.0)
    if gates:
        facts["gate_count"] = len(gates)
    composite_modules = sorted(SCORERS.glob("d*.py"))
    if composite_modules:
        facts.setdefault("composite_count", len(composite_modules))
        facts["hard_floor_declared"] = sum(
            1
            for path in composite_modules
            if "hard_floor" in path.read_text(encoding="utf-8", errors="ignore")
        )
    if GATES.exists():
        text = GATES.read_text(encoding="utf-8", errors="ignore")
        facts["aoi_generalizable_gates"] = len(
            re.findall(r"aoi_generalizable\s*=\s*True", text)
        )
        facts["manual_scorers"] = sum(
            len(re.findall(r"manual\s*=\s*True", path.read_text(encoding="utf-8", errors="ignore")))
            for path in sorted(SCORERS.glob("*.py"))
        )
    if REGISTRY.exists():
        try:
            docstring = ast.get_docstring(
                ast.parse(REGISTRY.read_text(encoding="utf-8"))
            )
        except SyntaxError:
            docstring = ""
        if docstring:
            facts["registry_anchors"] = len(
                set(re.findall(r"\bD\d+\b", docstring))
            )
    return facts


def _count_enumeration(text: str) -> int:
    """How many items an enumeration names ("a, b, c and d" -> 4)."""
    count = 0
    for part in text.split(","):
        count += len(re.split(r"\s+and\s+", part.strip()))
    return count


def prose_cardinality_report(
    docs: list[Path], facts: dict[str, int], sidecar_key_count: int
) -> list[str]:
    """Cardinalities a document states vs the counts the code has."""
    out: list[str] = []
    usable = dict(facts)
    if sidecar_key_count:
        usable["sidecar_key_count"] = sidecar_key_count
    for doc in docs:
        text = strip_verbatim(doc.read_text(encoding="utf-8"))
        rel = doc.relative_to(REPO)
        for claim in PROSE_CLAIMS:
            for match in claim["pattern"].finditer(text):
                stated: list[int] = []
                if claim.get("enumeration"):
                    count = _count_enumeration(match.group(1))
                    if count <= 0:
                        continue
                    stated.append(count)
                else:
                    for group in match.groups():
                        if group is None:
                            continue
                        word = group.lower()
                        if word not in NUMBER_WORDS:
                            stated = []
                            break
                        stated.append(NUMBER_WORDS[word])
                    if not stated:
                        continue
                expected = [usable.get(name) for name in claim["facts"]]
                if any(value is None for value in expected):
                    continue
                if stated != expected:
                    out.append(
                        f"{rel}: {claim['name']} says {stated} but the code "
                        f"has {expected}"
                    )
    return out


# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--changed", nargs="*", default=[], help="changed paths")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    report: dict[str, list[str]] = {
        "unknown_model_keys": [],
        "unknown_code_constants": [],
        "unknown_symbols": [],
        "missing_paths": [],
        "contract_versions": [],
        "contract_version_errors": [],
        "contract_file_mismatch": [],
        "contract_declaration_mismatch": [],
        "sidecar_key_mismatch": [],
        "prose_cardinality": [],
        "candidate_documents": [],
        "out_of_range_citations": [],
    }

    gen = _load_generator()
    values = model_values(gen)
    model_keys = known_model_keys(values, gen)
    code_constants = known_code_constants(gen)
    sections = {key.split(".")[0] for key in model_keys}
    tree = tree_text()
    tree_paths = {
        str(p.relative_to(REPO))
        for p in REPO.rglob("*")
        if p.is_file() and not _ignored(p.relative_to(REPO))
    }
    tree_dirs = {
        str(p.relative_to(REPO))
        for p in REPO.rglob("*")
        if p.is_dir() and not _ignored(p.relative_to(REPO))
    }

    docs = documents()

    for doc in docs:
        if doc.parent.name == "generated":
            # Generated fragments are built from the code; they are the
            # reference, not the thing to check.
            continue
        text = doc.read_text(encoding="utf-8")
        # A long path is broken across lines with \allowbreak; join it back
        # before looking for paths, or the signal reports a fragment.
        text = re.sub(r"\\allowbreak(\{\})?[ \t]*\n[ \t]*", "", text)
        text = text.replace("\\allowbreak{}", "")
        # A literal block holds pseudocode: its tokens are not markup.
        text = strip_verbatim(text)
        rel = doc.relative_to(REPO)

        for key in MSKEY_RE.findall(text):
            plain = _unescape(key)
            if not MODEL_KEY_RE.match(plain):
                continue
            if plain not in model_keys:
                report["unknown_model_keys"].append(
                    f"{rel}: \\mskey{{{key}}} (model-constant family)"
                )

        for key in CODE_CONST_RE.findall(text):
            plain = _unescape(key)
            if not CODE_KEY_RE.match(plain):
                continue
            if plain not in code_constants:
                report["unknown_code_constants"].append(
                    f"{rel}: \\codeconst{{{key}}} (code-constant family)"
                )

        for symbol in CODE_RE.findall(text):
            raw_token = symbol.strip()
            symbol = _unescape(raw_token)
            if not _LOOKS_LIKE_A_SYMBOL(symbol):
                continue
            parts = symbol.split(".")
            if len(parts) > 1 and parts[0] in sections:
                # A configuration key: check it against the generated macros.
                if symbol not in model_keys:
                    # A SECTION reference is legitimate prose (it carries no
                    # number); only an unknown LEAF is an error. And a name
                    # that is a code symbol (a function that shares a
                    # section's name) is a symbol, not a key.
                    if not any(k.startswith(symbol + ".") for k in model_keys):
                        if not _mentioned_in_tree(symbol, tree):
                            report["unknown_model_keys"].append(
                                f"{rel}: \\code{{{symbol}}} (model-constant family)"
                            )
                continue
            if _mentioned_in_tree(symbol, tree):
                continue
            if _introduced_here(text, raw_token):
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

    contracts = contracts_yaml(gen)
    mentions, errors = contract_version_report(docs, values)
    report["contract_versions"] = mentions
    report["contract_version_errors"] = errors
    report["contract_file_mismatch"] = contract_file_report(gen, values)
    report["contract_declaration_mismatch"] = contract_declaration_report(
        contracts, values, gen
    )

    code_sidecar = code_sidecar_keys(gen)
    report["sidecar_key_mismatch"] = sidecar_key_report(
        docs, code_sidecar, declared_sidecar_keys(contracts), tree
    )

    facts = scoring_facts(gen)
    report["prose_cardinality"] = prose_cardinality_report(
        docs, facts, len(code_sidecar)
    )

    report["out_of_range_citations"] = citation_report(docs)

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
