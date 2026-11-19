#!/usr/bin/env python3
"""Value generator for the conceptual documentation layer.

Reads the validated model constants (via the project's own loader, so the
configuration validator runs first and a renamed or removed key fails here),
harvests the unit annotations the YAML states in its comments ("Unidades
entre [ ]"), and emits LaTeX fragments into ``docs/concepts/generated/``:

* ``macros.tex``     -- ``\\mskey{<dotted.key>}`` per scalar key. A document
  that references a key which no longer exists fails the LaTeX build with an
  undefined control sequence: that is the guarantee, and it is a property of
  the build, not a judgement about the document.
* ``params-<stage>.tex`` -- the parameter table of one pipeline stage.
* ``contracts.tex``  -- the contract table, cross-checked against the C++
  headers that define the contract.

Deterministic: same inputs, byte-identical files.

Usage:
    uv run python tools/gen_concepts_values.py [--check]
"""
from __future__ import annotations

import argparse
import ast
import re
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "mal-core" / "src"))
sys.path.insert(0, str(REPO / "mal-commonlib" / "src"))

from mal_core.habitat.config import load_config, resolve_path  # noqa: E402

OUT_DIR = REPO / "docs" / "concepts" / "generated"
CONTRACTS_YAML = REPO / "docs" / "concepts" / "contracts.yaml"
ABM_INCLUDE = REPO / "mal-core" / "src" / "mal_core" / "abm" / "include" / "mal_abm_fast"

STAGES = ("download", "ingest", "abm", "scoring", "training", "prediction")

# Which top-level sections of model_constants.yaml each stage's document
# prints. Repetition between stages is deliberate (plan D5): the same fact
# written from two stages' points of view is where the drift shows up.
STAGE_SECTIONS: dict[str, tuple[str, ...]] = {
    "ingest": (
        "contracts",
        "ingest",
        "wildlife",
        "geodesy",
        "urban",
        "capacity",
        "pluvial",
        "habitat_types",
    ),
    "abm": (
        "contracts",
        "adults",
        "aquatic_stages",
        "aquatic_stress",
        "capacity",
        "dispersal",
        "eip",
        "geodesy",
        "gonotrophic",
        "habitat",
        "habitat_types",
        "host_seeking",
        "oviposition",
        "pluvial",
        "rng",
        "species",
        "thermal",
        "transmission",
        "urban",
    ),
}


# ---------------------------------------------------------------------------
# Units: harvested from the YAML's own comment convention.
# ---------------------------------------------------------------------------

_KEY_RE = re.compile(r"^(?P<indent>\s*)(?P<key>[A-Za-z_][A-Za-z0-9_]*)\s*:(?P<rest>.*)$")
_UNIT_RE = re.compile(r"#\s*\[(?P<unit>[^\]]+)\]")


def harvest_units(text: str) -> dict[str, str]:
    """Map dotted config paths to the unit annotated in the YAML comments.

    The YAML states "Unidades entre [ ]" in its header; each parameter
    carries its unit there. A value's own trailing comment wins; failing
    that, the next comment lines belonging to the same key. Keys inside a
    flow mapping inherit the parent's unit (e.g. the six habitat weights of
    a species row are all "fracción").
    """
    units: dict[str, str] = {}
    stack: list[tuple[int, str]] = []
    lines = text.splitlines()
    for i, line in enumerate(lines):
        m = _KEY_RE.match(line)
        if not m:
            continue
        indent = len(m.group("indent"))
        key = m.group("key")
        rest = m.group("rest").strip()
        while stack and stack[-1][0] >= indent:
            stack.pop()
        path = ".".join([k for _, k in stack] + [key])
        stack.append((indent, key))

        unit = None
        inline = _UNIT_RE.search(rest)
        if inline:
            unit = inline.group("unit").strip()
        else:
            # continuation comment lines (more indented, comment-only)
            j = i + 1
            while j < len(lines):
                nxt = lines[j].strip()
                if not nxt.startswith("#"):
                    break
                found = _UNIT_RE.search(nxt)
                if found:
                    unit = found.group("unit").strip()
                    break
                j += 1
        if rest.startswith("{") and rest.endswith("}"):
            # flow mapping: children share the parent's unit
            inner = rest[1:-1]
            for item in inner.split(","):
                if ":" not in item:
                    continue
                sub = item.split(":", 1)[0].strip()
                if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", sub):
                    continue
                if unit:
                    units[f"{path}.{sub}"] = unit
        if unit:
            units[path] = unit
    return units


# ---------------------------------------------------------------------------
# Values.
# ---------------------------------------------------------------------------


def flatten(cfg: Mapping[str, Any], prefix: str = "") -> dict[str, Any]:
    """Flatten the validated config into dotted paths (scalars only)."""
    out: dict[str, Any] = {}
    for key, value in cfg.items():
        path = f"{prefix}{key}"
        if isinstance(value, Mapping):
            out.update(flatten(value, f"{path}."))
        elif isinstance(value, (list, tuple)):
            out[path] = ", ".join(str(v) for v in value)
        else:
            out[path] = value
    return out


def latex_escape(text: str) -> str:
    repl = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(repl.get(c, c) for c in text)


def format_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return repr(value)
    if isinstance(value, int):
        return str(value)
    # A string value is a version, a name or a class: the quotes keep it
    # distinguishable from a number of the same digits (e.g. "4.0" vs 4.0).
    return f'"{value}"'


# ---------------------------------------------------------------------------
# Who reads a key. A parameter table that lists a key nobody reads is a
# claim the reader cannot check; a table that says who reads it is.
# ---------------------------------------------------------------------------

_PY_READER_RE = re.compile(
    r'model_constant\(\s*"([^"]+)"\s*,\s*"([^"]+)"\s*\)'
)
# A whole section read into a variable, then a leaf read out of it:
#   _INGEST = _MODEL_CONSTANTS["ingest"]
#   COASTLINE_BUFFER_M_DEFAULT = float(_INGEST["coastline_buffer_m"])
_PY_SECTION_RE = re.compile(
    r'(\w+)\s*=\s*([\w\.]*\[?\s*"([a-z_]+)"\s*\])', re.MULTILINE
)
_PY_LEAF_RE = re.compile(r'(\w+)\s*\[\s*"([a-z_0-9]+)"\s*\]')
# A helper that reads a key whose name is a variable:
#   def _config_float(key, fallback): return float(model_constant("ingest", key))
#   _config_float("coastline_resolution", ...)
_PY_VARIABLE_KEY_HELPER_RE = re.compile(
    r'def\s+(_config_\w+)\([^)]*\)[^:]*:(.*?)(?=\ndef\s|\Z)', re.S
)
_PY_HELPER_CALL_RE = re.compile(r'\b(_config_\w+)\(\s*"([a-z_0-9]+)"')
_CPP_READER_RE = re.compile(
    r'L\.key\(\s*[^,]+,\s*"([^"]+)"\s*,\s*"([^"]+)"\s*\)'
)
# A row read inside a loop over the species names:
#   L.key(row, std::string("species.") + name, "salinity_opt_ppt")
# The section is known, the leaf is known, the row in between is not.
_CPP_ROW_READER_RE = re.compile(
    r'L\.key\(\s*[^,]+,\s*[^,]*?"([a-z_]+)\."\s*\)?\s*\+\s*\w+\s*,\s*"([a-z_0-9]+)"\s*\)'
)

_READER_ROOTS = (
    "mal-commonlib/src",
    "mal-core/src",
    "mal-execution",
)
# The C++ loader reads a key into the configuration struct; whether the
# engine ACTS on it is a second question, and the difference matters: a
# key that is loaded and never used is a parameter that does nothing.
_LOADER_ONLY_FILES = {
    "mal-core/src/mal_core/abm/src/config.cc",
    "mal-core/src/mal_core/abm/src/config_dump.cpp",
}
_READER_INDEX: dict[str, set[str]] | None = None
_ROW_LEAF_INDEX: dict[tuple[str, str], set[str]] | None = None
_FIELD_USE_INDEX: dict[str, set[str]] | None = None


def _scan_readers() -> tuple[
    dict[str, set[str]], dict[tuple[str, str], set[str]], dict[str, set[str]]
]:
    """Map every dotted config key to the files that read it.

    Two access patterns carry the whole configuration: the Python side
    calls ``model_constant("section", "key")``; the C++ engine's loader
    calls ``L.key(node, "section", "key")``. A key that appears in neither
    is DECLARED ONLY -- it is in the schema and in the validator, and no
    production code consumes it.

    Returns three indexes: the exact one; a second one for the leaves a
    C++ row read touches (``(section, leaf)``), because a row is read in a
    loop over the species names and the row's own name is not a literal;
    and a third one mapping a C++ field name to the files that mention it
    outside the loader, which is how a LOADED parameter is told apart from
    a USED one.
    """
    index: dict[str, set[str]] = {}
    row_leaf: dict[tuple[str, str], set[str]] = {}
    fields: dict[str, set[str]] = {}
    for root in _READER_ROOTS:
        base = REPO / root
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            if path.suffix not in (".py", ".cc", ".cpp", ".hpp", ".h"):
                continue
            if "tests" in path.parts or path.name.startswith("test_"):
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            label = f"{root.split('/')[-1]}/{path.relative_to(base)}"
            label = str(path.relative_to(REPO))
            for section, key in _PY_READER_RE.findall(text):
                index.setdefault(f"{section}.{key}", set()).add(label)
            # A section held in a variable: the leaves read out of it are
            # read by this file.
            section_vars: dict[str, str] = {}
            for var, rhs, section in _PY_SECTION_RE.findall(text):
                if "constant" in rhs.lower():
                    section_vars[var] = section
            for var, leaf in _PY_LEAF_RE.findall(text):
                section = section_vars.get(var)
                if section:
                    index.setdefault(f"{section}.{leaf}", set()).add(label)
            # A helper that reads a key given as a variable.
            helper_sections: dict[str, str] = {}
            for helper, body in _PY_VARIABLE_KEY_HELPER_RE.findall(text):
                m = re.search(
                    r'model_constant\(\s*"([a-z_]+)"\s*,\s*\w+\s*\)', body
                )
                if m:
                    helper_sections[helper] = m.group(1)
            for helper, leaf in _PY_HELPER_CALL_RE.findall(text):
                section = helper_sections.get(helper)
                if section:
                    index.setdefault(f"{section}.{leaf}", set()).add(label)
            for section, key in _CPP_READER_RE.findall(text):
                index.setdefault(f"{section}.{key}", set()).add(label)
            for section, leaf in _CPP_ROW_READER_RE.findall(text):
                row_leaf.setdefault((section, leaf), set()).add(label)
            if path.suffix in (".cc", ".cpp", ".hpp", ".h"):
                for name in re.findall(r"\b([a-z][a-z_0-9]{3,})\b", text):
                    fields.setdefault(name, set()).add(label)
    return index, row_leaf, fields


def _readers_of(key: str) -> list[str]:
    """The files that read ``key``; empty when no production code does.

    A section can be read whole (``model_constant("wildlife",
    "class_suitability")`` returns the mapping), so a leaf inherits the
    readers of its longest read prefix.
    """
    global _READER_INDEX, _ROW_LEAF_INDEX, _FIELD_USE_INDEX
    if _READER_INDEX is None or _ROW_LEAF_INDEX is None or _FIELD_USE_INDEX is None:
        _READER_INDEX, _ROW_LEAF_INDEX, _FIELD_USE_INDEX = _scan_readers()
    parts = key.split(".")
    readers: set[str] = set()
    for cut in range(len(parts), 0, -1):
        prefix = ".".join(parts[:cut])
        found = _READER_INDEX.get(prefix)
        if found:
            readers = set(found)
            break
    else:
        # A leaf read inside a row loop: species.arabiensis.salinity_opt_ppt
        # is read by whoever reads species.salinity_opt_ppt. A whole MAP
        # read in a row loop (the species weights) covers its leaves.
        for cut in (len(parts) - 1, len(parts) - 2):
            if cut < 1:
                continue
            found = _ROW_LEAF_INDEX.get((parts[0], parts[cut]))
            if found:
                readers = set(found)
                break
    if not readers:
        return []
    used_elsewhere: set[str] = set()
    for reader in readers:
        if reader in _LOADER_ONLY_FILES:
            continue
        used_elsewhere.add(reader)
    if readers & _LOADER_ONLY_FILES:
        field = parts[-1]
        for name in _FIELD_USE_INDEX.get(field, set()):
            if name not in _LOADER_ONLY_FILES:
                used_elsewhere.add(name)
    if used_elsewhere:
        struct_only = {
            f for f in used_elsewhere if f.endswith("abm_fast/config.hpp")
        }
        if struct_only and not (used_elsewhere - struct_only):
            # The value reaches the configuration struct and nothing else:
            # the parameter is loaded and has no effect.
            return ["(loaded, never used)"]
        return sorted(used_elsewhere)
    return sorted(readers)


# ---------------------------------------------------------------------------
# C++ cross-checks: the contract the C++ engine implements.
# ---------------------------------------------------------------------------

BAND_RE = re.compile(r'STATE_BAND_NAMES\[2\]\s*=\s*\{([^}]*)\}')


def cpp_band_names() -> list[str]:
    text = (ABM_INCLUDE / "wire.hpp").read_text(encoding="utf-8")
    m = BAND_RE.search(text)
    if not m:
        raise SystemExit("gen_concepts_values: cannot find STATE_BAND_NAMES in wire.hpp")
    return re.findall(r'"([^"]+)"', m.group(1))


def cpp_sidecar_keys() -> list[str]:
    text = (REPO / "mal-core/src/mal_core/abm/src/output_contract.cpp").read_text(
        encoding="utf-8"
    )
    return re.findall(r'j\["([^"]+)"\]\s*=', text)


def read_contracts_yaml() -> dict[str, Any]:
    """Minimal reader for the contracts file (flat, two levels)."""
    import yaml

    data = yaml.safe_load(CONTRACTS_YAML.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "artefacts" not in data:
        raise SystemExit(
            "gen_concepts_values: docs/concepts/contracts.yaml must hold an "
            "'artefacts' list"
        )
    return data


def cross_check_contracts(
    contracts: dict[str, Any], values: Mapping[str, Any], bands: list[str]
) -> list[str]:
    """Fail the build when the contracts file disagrees with the code."""
    problems: list[str] = []
    for art in contracts["artefacts"]:
        key = art.get("key")
        version_from = art.get("version_from")
        if version_from and version_from in values:
            if art.get("version") and art["version"] != values[version_from]:
                problems.append(
                    f"{key}: contracts.yaml version {art['version']!r} != "
                    f"model_constants.yaml {version_from} {values[version_from]!r}"
                )
        elif version_from:
            problems.append(
                f"{key}: contracts.yaml version_from {version_from!r} is not a "
                "known model constant"
            )
        if art.get("bands") and list(art["bands"]) != bands:
            problems.append(
                f"{key}: contracts.yaml bands {art['bands']} != wire.hpp "
                f"STATE_BAND_NAMES {bands}"
            )
        sentinel = art.get("sentinel")
        if sentinel is not None and not isinstance(sentinel, (int, float)):
            # The word `none` declares that the artefact carries no no-data
            # marker of its own; any other string is a mistake in the file.
            if str(sentinel).strip().lower() != "none":
                problems.append(
                    f"{key}: contracts.yaml sentinel {sentinel!r} is neither a "
                    "number nor the word 'none'"
                )
        elif sentinel is not None:
            real = values.get("ingest.nodata_sentinel")
            if real is not None and float(sentinel) != float(real):
                problems.append(
                    f"{key}: contracts.yaml sentinel {sentinel} != "
                    f"ingest.nodata_sentinel {real}"
                )
    return problems


# ---------------------------------------------------------------------------
# Emission.
# ---------------------------------------------------------------------------


def emit_macros(values: dict[str, Any]) -> str:
    out = [
        "% Generated by tools/gen_concepts_values.py -- do not edit.",
        "% Values come from mal-core/config/model_constants.yaml via the",
        "% validated loader; a key that no longer exists makes \\mskey fail",
        "% the build with an error, in any document that references it.",
        "",
        "\\makeatletter",
        "\\newcommand{\\mskey}[1]{%",
        "  \\expandafter\\ifx\\csname ms@k@#1\\endcsname\\relax",
        "    \\errmessage{Concept document: unknown model constant key `#1'}%",
        "  \\else",
        "    \\csname ms@k@#1\\endcsname%",
        "  \\fi}",
        "\\makeatother",
        "",
    ]
    for key in sorted(values):
        out.append(
            f"\\expandafter\\def\\csname ms@k@{key}\\endcsname"
            f"{{{latex_escape(format_value(values[key]))}}}"
        )
    out.append("")
    return "\n".join(out)


def emit_params_table(
    rows: list[tuple[str, str, str]], title: str
) -> str:
    out = [
        "% Generated by tools/gen_concepts_values.py -- do not edit.",
        f"\\paragraph{{{latex_escape(title)}}}",
        "\\begin{longtable}{@{}llll@{}}",
        "\\toprule",
        "Key & Value & Unit & Read by \\\\",
        "\\midrule",
        "\\endhead",
    ]
    for key, value, unit in rows:
        readers = _readers_of(key)
        if not readers:
            who = "— (declared only)"
        elif len(readers) <= 3:
            who = ", ".join(readers)
        else:
            who = ", ".join(readers[:2]) + f" … (+{len(readers) - 2} more)"
        out.append(
            f"\\code{{{latex_escape(key)}}} & {latex_escape(value)} & "
            f"{latex_escape(unit) if unit else '---'} & {latex_escape(who)} \\\\"
        )
    out.append("\\bottomrule")
    out.append("\\end{longtable}")
    out.append("")
    return "\n".join(out)


def emit_download_params() -> str:
    """The download stage's table: the dataset registry and the AOI registry."""
    from mal_core.download.registry import discover_downloaders
    from mal_commonlib.aoi import AOI, _load_aois_yaml

    out = [
        "% Generated by tools/gen_concepts_values.py -- do not edit.",
        "\\paragraph{The dataset registry (the identity of every downloadable product)}",
        "\\begin{longtable}{@{}lllll@{}}",
        "\\toprule",
        "Dataset & Manifest keys & Authentication & Reduction & Module \\\\",
        "\\midrule",
        "\\endhead",
    ]
    downloaders = discover_downloaders()
    for name in sorted(downloaders):
        spec = downloaders[name]
        auth = ", ".join(spec.requires_auth) if spec.requires_auth else "none"
        keys = ", ".join(sorted(spec.manifest_keys)) if spec.manifest_keys else "---"
        red = (
            ", ".join(f"{k}: {v}" for k, v in sorted(spec.reductions.items()))
            if spec.reductions
            else "---"
        )
        out.append(
            f"{latex_escape(spec.name)} & {latex_escape(keys)} & "
            f"{latex_escape(auth)} & {latex_escape(red)} & "
            f"\\code{{{latex_escape(spec.module_name)}}} \\\\"
        )
    out.append("\\bottomrule")
    out.append("\\end{longtable}")
    out.append("")

    out.append(
        "\\paragraph{The area-of-interest registry (the spatial frame every "
        "stage agrees on)}"
    )
    out.append("\\begin{longtable}{@{}llllll@{}}")
    out.append("\\toprule")
    out.append("Slug & Name & Bounding box & CRS & Cell size (m) & Scale & Grid \\\\")
    out.append("\\midrule")
    out.append("\\endhead")
    for slug in sorted(_load_aois_yaml()):
        payload = _load_aois_yaml()[slug]
        aoi = AOI.from_slug(slug)
        h, w = aoi.cells_per_side()
        out.append(
            f"\\code{{{latex_escape(slug)}}} & {latex_escape(str(payload.get('name', '')))} & "
            f"\\code{{{latex_escape(str(payload.get('bbox')))}}} & "
            f"\\code{{{latex_escape(str(payload.get('crs')))}}} & "
            f"{latex_escape(str(payload.get('resolution_m')))} & "
            f"{latex_escape(str(payload.get('scale')))} & "
            f"{h} x {w} \\\\"
        )
    out.append("\\bottomrule")
    out.append("\\end{longtable}")
    out.append("")
    return "\n".join(out)


def emit_scoring_params() -> str:
    """The scoring stage's table: composite weights, gates, thresholds."""
    from mal_core.scoring.registry import (
        COMPOSITE_WEIGHTS,
        GATES,
        build_registry,
    )

    registry = build_registry()
    # The table must be COMPLETE: a dimension the registry knows but the
    # weight table does not is a dimension the document cannot state.
    missing = sorted(
        name
        for name, spec in registry.items()
        if spec.kind == "composite" and name not in COMPOSITE_WEIGHTS
    )
    if missing:
        raise SystemExit(
            "gen_concepts_values: composite scorers without a weight in "
            f"COMPOSITE_WEIGHTS: {missing}"
        )
    ungated = sorted(
        name
        for name, spec in registry.items()
        if spec.kind == "gate" and name not in GATES
    )
    if ungated:
        raise SystemExit(
            f"gen_concepts_values: gates missing from GATES: {ungated}"
        )
    out = [
        "% Generated by tools/gen_concepts_values.py -- do not edit.",
        "\\paragraph{Composite dimensions and their weights}",
        "\\begin{longtable}{@{}llrl@{}}",
        "\\toprule",
        "Dimension & Weight & Min. score & Hard floor \\\\",
        "\\midrule",
        "\\endhead",
    ]
    for name in sorted(COMPOSITE_WEIGHTS):
        scorer = registry[name].cls()
        out.append(
            f"\\code{{{latex_escape(name)}}} & {format_value(COMPOSITE_WEIGHTS[name])} & "
            f"{format_value(getattr(scorer, 'min_score', ''))} & "
            f"{format_value(getattr(scorer, 'hard_floor', ''))} \\\\"
        )
    out.append("\\bottomrule")
    out.append("\\end{longtable}")
    out.append("")

    out.append("\\paragraph{Gates (evaluated separately from the composite)}")
    out.append("\\begin{longtable}{@{}ll@{}}")
    out.append("\\toprule")
    out.append("Gate & Description \\\\")
    out.append("\\midrule")
    out.append("\\endhead")
    for name in GATES:
        scorer = registry[name].cls()
        out.append(
            f"\\code{{{latex_escape(name)}}} & "
            f"{latex_escape(getattr(scorer, 'description', ''))} \\\\"
        )
    out.append("\\bottomrule")
    out.append("\\end{longtable}")
    out.append("")
    return "\n".join(out)


def _function_defaults(path: Path, qualname: str) -> dict[str, Any]:
    """Read a function's default arguments from the source, without importing.

    The training module imports torch; the values it defines must be
    readable in a documentation build that does not need the training
    stack. The AST is the source of truth for a default argument.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    targets: list[ast.FunctionDef] = []
    if "." in qualname:
        cls_name, meth = qualname.split(".", 1)
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == cls_name:
                targets = [
                    n
                    for n in node.body
                    if isinstance(n, ast.FunctionDef) and n.name == meth
                ]
    else:
        targets = [
            n
            for n in ast.walk(tree)
            if isinstance(n, ast.FunctionDef) and n.name == qualname
        ]
    for node in targets:
        out: dict[str, Any] = {}
        args = node.args
        defaults = list(args.defaults)
        names = [a.arg for a in args.args][-len(defaults) :] if defaults else []
        for name, default in zip(names, defaults):
            try:
                out[name] = ast.literal_eval(default)
            except ValueError:
                out[name] = ast.unparse(default)
        return out
    raise SystemExit(f"gen_concepts_values: {qualname} not found in {path}")


def emit_training_params() -> str:
    """The training stage's table: the surrogate's shape and its defaults."""
    training = REPO / "mal-core" / "src" / "mal_core" / "training"
    model_defaults = _function_defaults(training / "model.py", "UNet.__init__")
    train_defaults = _function_defaults(training / "trainer.py", "train_unet")

    out = [
        "% Generated by tools/gen_concepts_values.py -- do not edit.",
        "\\paragraph{The surrogate's architecture}",
        "\\begin{longtable}{@{}ll@{}}",
        "\\toprule",
        "Element & Value \\\\",
        "\\midrule",
        "\\endhead",
    ]
    for name, value in model_defaults.items():
        out.append(
            f"\\code{{{latex_escape(name)}}} & "
            f"{latex_escape(str(value))} \\\\"
        )
    out.append("\\bottomrule")
    out.append("\\end{longtable}")
    out.append("")

    out.append("\\paragraph{The training loop's defaults}")
    out.append("\\begin{longtable}{@{}ll@{}}")
    out.append("\\toprule")
    out.append("Argument & Default \\\\")
    out.append("\\midrule")
    out.append("\\endhead")
    for name, value in train_defaults.items():
        if name in ("run_dir", "output_dir"):
            continue
        out.append(f"\\code{{{latex_escape(name)}}} & {latex_escape(str(value))} \\\\")
    out.append("\\bottomrule")
    out.append("\\end{longtable}")
    out.append("")
    return "\n".join(out)


def emit_prediction_params() -> str:
    """The prediction stage's table: what it consumes and produces."""
    out = [
        "% Generated by tools/gen_concepts_values.py -- do not edit.",
        "\\paragraph{The bands the prediction consumes (the state contract)}",
        "\\begin{longtable}{@{}ll@{}}",
        "\\toprule",
        "Band & Meaning \\\\",
        "\\midrule",
        "\\endhead",
    ]
    meanings = {
        "adult_patch_count": "adults associated with their patch, post-dispersal",
        "adult_cell_count": "adults at their current cell",
    }
    for band in cpp_band_names():
        out.append(
            f"\\code{{{latex_escape(band)}}} & "
            f"{latex_escape(meanings.get(band, ''))} \\\\"
        )
    out.append("\\bottomrule")
    out.append("\\end{longtable}")
    out.append("")
    return "\n".join(out)


def emit_contracts(
    contracts: dict[str, Any], cfg: Mapping[str, Any], values: Mapping[str, Any]
) -> str:
    out = [
        "% Generated by tools/gen_concepts_values.py -- do not edit.",
        "\\paragraph{The output contracts}",
        "\\begin{longtable}{@{}llllll@{}}",
        "\\toprule",
        "Artefact & Producer & Consumers & Version & Bands / variables & "
        "Sentinel \\\\",
        "\\midrule",
        "\\endhead",
    ]
    for art in contracts["artefacts"]:
        bands = art.get("bands") or art.get("variables") or []
        version = art.get("version") or ""
        if not version and art.get("version_from"):
            version = format_value(values.get(art["version_from"], ""))
        out.append(
            f"\\code{{{latex_escape(str(art.get('key')))}}} & "
            f"\\code{{{latex_escape(str(art.get('producer')))}}} & "
            f"{latex_escape(', '.join(art.get('consumers', [])))} & "
            f"{latex_escape(str(version))} & "
            f"{latex_escape(', '.join(bands))} & "
            f"{latex_escape(str(art.get('sentinel', '')))} \\\\"
        )
    out.append("\\bottomrule")
    out.append("\\end{longtable}")
    out.append("")

    out.append("\\paragraph{The state sidecar's keys, in emission order}")
    out.append("\\begin{longtable}{@{}l@{}}")
    out.append("\\toprule")
    out.append("Key \\\\")
    out.append("\\midrule")
    out.append("\\endhead")
    for key in cpp_sidecar_keys():
        out.append(f"\\code{{{latex_escape(key)}}} \\\\")
    out.append("\\bottomrule")
    out.append("\\end{longtable}")
    out.append("")
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Code constants: the second macro family.
#
# The YAML holds the parameters the CONFIGURATION states. Many of the
# numbers a conceptual document must state are not configuration: they are
# literals in the code that implements the stage (a channel count, a
# threshold, a band's edges). Those are read here, by AST, from the source
# file that owns them -- never by importing the module (the training stack
# pulls in torch, and a documentation build must not need it) and never by
# typing the value into this generator.
#
# Every emitted macro carries the ``file:line`` it came from, so the
# document can cite the code and the generator can prove the citation: if
# the source disappears, the generator fails loudly instead of emitting a
# macro nobody can justify.
# ---------------------------------------------------------------------------

import ast
from dataclasses import dataclass
from typing import Any

TRAINING_DIR = "mal-core/src/mal_core/training"
PREDICTION_DIR = "mal-core/src/mal_core/prediction"
SCORING_DIR = "mal-core/src/mal_core/scoring"
INGEST_DIR = "mal-core/src/mal_core/ingest"
HABITAT_DIR = "mal-core/src/mal_core/habitat"
LOADERS_DIR = "mal-commonlib/src/mal_commonlib/data/loaders"


@dataclass(frozen=True)
class CodeValue:
    """One value read from the code, with the place it was read from."""

    value: Any
    source: str  # "repo/relative/path.py:LINE"


class CodeSpecError(SystemExit):
    """Raised when a source the generator depends on can no longer be read."""


def _fail(message: str) -> None:
    raise CodeSpecError(f"gen_concepts_values: {message}")


def _source(path: str) -> Path:
    return REPO / path


def _text(path: str) -> str:
    full = _source(path)
    try:
        return full.read_text(encoding="utf-8")
    except OSError as exc:
        _fail(f"cannot read {path}: {exc}")
        raise  # unreachable, keeps the type checker happy


def _tree(path: str) -> ast.Module:
    try:
        return ast.parse(_text(path))
    except SyntaxError as exc:
        _fail(f"cannot parse {path}: {exc}")
        raise


# ---------------------------------------------------------------------------
# AST primitives.
# ---------------------------------------------------------------------------


def _numeric(node: ast.AST) -> Any:
    """Evaluate a numeric expression made of constants (``0.143 * 9.3 * 1e6``)."""
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        value = _numeric(node.operand)
        return -value if isinstance(node.op, ast.USub) else value
    if isinstance(node, ast.BinOp):
        left = _numeric(node.left)
        right = _numeric(node.right)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.Div):
            return left / right
    raise ValueError(f"not a numeric expression: {ast.dump(node)}")


def _value_of(node: ast.AST) -> Any:
    """The value of a node: a literal, or a numeric expression of literals."""
    try:
        return ast.literal_eval(node)
    except (ValueError, SyntaxError, TypeError):
        return _numeric(node)


def _maybe_value(node: ast.AST) -> Any:
    """The value of a node, or None when it is not a literal we can read."""
    try:
        return _value_of(node)
    except (ValueError, SyntaxError, TypeError):
        return None


def _module_bindings(path: str) -> dict[str, tuple[Any, int]]:
    """Module-level bindings: name -> (value, line).

    A tuple target binds several names at once (``P50_CENTER, P50_SIGMA =
    0.40, 0.20``); each name keeps the line of its own element. Only the
    module's own statements are read: a local assignment inside a function
    does not shadow the module constant of the same name.
    """
    out: dict[str, tuple[Any, int]] = {}
    for node in _tree(path).body:
        if isinstance(node, ast.Assign):
            tuple_target = (
                len(node.targets) == 1
                and isinstance(node.targets[0], (ast.Tuple, ast.List))
                and isinstance(node.value, (ast.Tuple, ast.List))
            )
            if not tuple_target:
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        value = _maybe_value(node.value)
                        if value is not None:
                            out[target.id] = (value, node.value.lineno)
                continue
            for target, element in zip(node.targets[0].elts, node.value.elts):
                if isinstance(target, ast.Name):
                    value = _maybe_value(element)
                    if value is not None:
                        out[target.id] = (value, element.lineno)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            if node.value is not None:
                value = _maybe_value(node.value)
                if value is not None:
                    out[node.target.id] = (value, node.value.lineno)
    return out


def _class_bindings(path: str) -> dict[tuple[str, str], tuple[Any, int]]:
    """Class attributes: (class, attribute) -> (value, line)."""
    out: dict[tuple[str, str], tuple[Any, int]] = {}
    for node in ast.walk(_tree(path)):
        if not isinstance(node, ast.ClassDef):
            continue
        for item in node.body:
            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                if item.value is not None:
                    value = _maybe_value(item.value)
                    if value is not None:
                        out[(node.name, item.target.id)] = (
                            value,
                            item.value.lineno,
                        )
            elif isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        value = _maybe_value(item.value)
                        if value is not None:
                            out[(node.name, target.id)] = (
                                value,
                                item.value.lineno,
                            )
    return out


def _function_def(path: str, qualname: str) -> ast.FunctionDef:
    cls_name, _, meth = qualname.rpartition(".")
    for node in ast.walk(_tree(path)):
        if isinstance(node, ast.ClassDef) and cls_name:
            if node.name == cls_name:
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and item.name == meth:
                        return item
        elif isinstance(node, ast.FunctionDef) and not cls_name:
            if node.name == qualname:
                return node
    _fail(f"{qualname} not found in {path}")
    raise  # unreachable


def _defaults(path: str, qualname: str) -> dict[str, tuple[Any, int]]:
    """A function's default arguments: name -> (value, line)."""
    func = _function_def(path, qualname)
    out: dict[str, tuple[Any, int]] = {}
    args = func.args
    defaults = list(args.defaults)
    names = [a.arg for a in args.args][-len(defaults) :] if defaults else []
    for name, default in zip(names, defaults):
        out[name] = (_value_of(default), default.lineno)
    # keyword-only arguments carry their own defaults.
    kw_defaults = list(args.kw_defaults)
    kw_names = [a.arg for a in args.kwonlyargs]
    for name, default in zip(kw_names, kw_defaults):
        if default is None:
            continue
        out[name] = (_value_of(default), default.lineno)
    return out


def _line_literals(path: str, lineno: int, want: str) -> list[Any]:
    """The literal constants of one source line, in source order.

    ``want`` is ``"num"`` (numeric constants) or ``"str"`` (string
    constants). A constant that spans several lines is attributed to the
    line it starts on.
    """
    out: list[tuple[int, int, Any]] = []
    tree = _tree(path)
    signed: set[int] = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.UnaryOp)
            and isinstance(node.op, ast.USub)
            and isinstance(node.operand, ast.Constant)
            and isinstance(node.operand.value, (int, float))
        ):
            if node.lineno != lineno:
                continue
            signed.add(id(node.operand))
            out.append(
                (
                    node.col_offset,
                    node.lineno,
                    -node.operand.value,
                )
            )
    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant):
            continue
        if id(node) in signed:
            continue
        if node.lineno != lineno:
            continue
        if want == "num" and isinstance(node.value, bool):
            continue
        if want == "num" and not isinstance(node.value, (int, float)):
            continue
        if want == "str" and not isinstance(node.value, str):
            continue
        out.append((node.col_offset, node.lineno, node.value))
    out.sort()
    return [value for _, _, value in out]


def _match_line(path: str, pattern: str, occurrence: int = 0) -> int:
    """The 1-based line number matching ``pattern`` (the N-th match)."""
    hits = [
        index
        for index, line in enumerate(_text(path).splitlines(), start=1)
        if re.search(pattern, line)
    ]
    if not hits:
        _fail(f"{path}: no line matches {pattern!r} (the source moved)")
    if occurrence >= len(hits):
        _fail(f"{path}: pattern {pattern!r} has {len(hits)} matches, wanted #{occurrence}")
    return hits[occurrence]


def _select(values: list[Any], index: Any, path: str, what: str) -> Any:
    if not values:
        _fail(f"{path}: {what} has no literal to read")
    if index == "last":
        return values[-1]
    if not isinstance(index, int) or index >= len(values):
        _fail(f"{path}: {what} has {len(values)} literals, wanted index {index!r}")
    return values[index]


# ---------------------------------------------------------------------------
# The specification: what to read, and from where.
#
# Each entry names the value a document may cite. The VALUE is never
# written here -- only the place it lives (a constant's name, a pattern
# that identifies the line that owns it).
# ---------------------------------------------------------------------------

CODE_SPECS: tuple[dict[str, Any], ...] = (
    # --- training -------------------------------------------------------
    {
        "name": "training.patch_size",
        "path": f"{TRAINING_DIR}/dataset.py",
        "kind": "module",
        "args": {"const": "PATCH_SIZE"},
    },
    {
        "name": "training.vector_channels",
        "path": f"{TRAINING_DIR}/dataset.py",
        "kind": "module",
        "args": {"const": "VECTOR_CHANNELS"},
    },
    {
        "name": "training.transmission_channels",
        "path": f"{TRAINING_DIR}/dataset.py",
        "kind": "module",
        "args": {"const": "TRANSMISSION_CHANNELS"},
    },
    {
        "name": "training.env_channels",
        "path": f"{TRAINING_DIR}/dataset.py",
        "kind": "module",
        "args": {"const": "ENV_CHANNELS"},
    },
    {
        "name": "training.sub_seed",
        "path": f"{TRAINING_DIR}/dataset.py",
        "kind": "line",
        "args": {"pattern": r"np\.random\.seed\(", "index": 0},
    },
    {
        "name": "training.unet_channels",
        "path": f"{TRAINING_DIR}/model.py",
        "kind": "default",
        "args": {"qualname": "UNet.__init__", "arg": "channels"},
    },
    {
        "name": "training.dice_tau",
        "path": f"{TRAINING_DIR}/model.py",
        "kind": "default",
        "args": {"qualname": "soft_dice_loss", "arg": "tau"},
    },
    {
        "name": "training.dice_thresh",
        "path": f"{TRAINING_DIR}/model.py",
        "kind": "default",
        "args": {"qualname": "soft_dice_loss", "arg": "thresh"},
    },
    {
        "name": "training.dice_count_threshold",
        "path": f"{TRAINING_DIR}/model.py",
        "kind": "default",
        "args": {"qualname": "eval_dice", "arg": "thresh"},
    },
    {
        "name": "training.dice_weight",
        "path": f"{TRAINING_DIR}/model.py",
        "kind": "line",
        "args": {"pattern": r"loss = mse \+ ", "index": 0},
    },
    {
        "name": "training.dice_eps",
        "path": f"{TRAINING_DIR}/model.py",
        "kind": "line",
        "args": {"pattern": r"dice = \(2 \* inter", "index": 1},
    },
    {
        "name": "training.ckpt_period",
        "path": f"{TRAINING_DIR}/trainer.py",
        "kind": "line",
        "args": {"pattern": r"if \(epoch \+ 1\) % ", "index": 1},
    },
    {
        "name": "training.pad_multiple",
        "path": f"{TRAINING_DIR}/wrapper.py",
        "kind": "line",
        "args": {"pattern": r"pad_h = \(16 - ", "index": 0},
    },
    {
        "name": "training.fallback_in_channels",
        "path": f"{TRAINING_DIR}/wrapper.py",
        "kind": "line",
        "args": {"pattern": r"in_channels = first_w\.shape", "index": 1},
    },
    {
        "name": "training.fallback_out_channels",
        "path": f"{TRAINING_DIR}/wrapper.py",
        "kind": "line",
        "args": {"pattern": r"out_channels = head_w\.shape", "index": 1},
    },
    # --- prediction -----------------------------------------------------
    {
        "name": "prediction.in_channels",
        "path": f"{PREDICTION_DIR}/registry.py",
        "kind": "class",
        "args": {"cls": "ModelManifest", "attr": "in_channels"},
    },
    {
        "name": "prediction.out_channels",
        "path": f"{PREDICTION_DIR}/registry.py",
        "kind": "class",
        "args": {"cls": "ModelManifest", "attr": "out_channels"},
    },
    {
        "name": "prediction.manifest_version",
        "path": f"{PREDICTION_DIR}/registry.py",
        "kind": "class",
        "args": {"cls": "ModelManifest", "attr": "version"},
    },
    {
        "name": "prediction.contract_version_manifest",
        "path": f"{PREDICTION_DIR}/registry.py",
        "kind": "class",
        "args": {"cls": "ModelManifest", "attr": "contract_version"},
    },
    {
        "name": "prediction.contract_version_sidecar",
        "path": f"{PREDICTION_DIR}/predictor.py",
        "kind": "line",
        "args": {"pattern": r'"contract_version": ', "index": "last", "want": "str"},
    },
    {
        "name": "prediction.scale_regional_m",
        "path": f"{PREDICTION_DIR}/aggregator.py",
        "kind": "scale",
        "args": {"scale": "REGIONAL"},
    },
    {
        "name": "prediction.scale_national_m",
        "path": f"{PREDICTION_DIR}/aggregator.py",
        "kind": "scale",
        "args": {"scale": "NATIONAL"},
    },
    {
        "name": "prediction.scale_continental_m",
        "path": f"{PREDICTION_DIR}/aggregator.py",
        "kind": "scale",
        "args": {"scale": "CONTINENTAL"},
    },
    {
        "name": "prediction.block_size",
        "path": f"{PREDICTION_DIR}/predictor.py",
        "kind": "line",
        "args": {"pattern": r'"blockxsize": ', "index": 0},
    },
    # --- scoring: verdicts and feedback --------------------------------
    {
        "name": "scoring.verdict_viable",
        "path": f"{SCORING_DIR}/runner.py",
        "kind": "tuple",
        "args": {"const": "VERDICTS", "path": (0, 0)},
    },
    {
        "name": "scoring.verdict_borderline",
        "path": f"{SCORING_DIR}/runner.py",
        "kind": "tuple",
        "args": {"const": "VERDICTS", "path": (1, 0)},
    },
    {
        "name": "scoring.verdict_regressed",
        "path": f"{SCORING_DIR}/runner.py",
        "kind": "tuple",
        "args": {"const": "VERDICTS", "path": (2, 0)},
    },
    {
        "name": "scoring.regression_threshold",
        "path": f"{SCORING_DIR}/feedback.py",
        "kind": "line",
        "args": {"pattern": r"if d < ", "index": 0},
    },
    # --- scoring: D1 ----------------------------------------------------
    {
        "name": "scoring.d1_band_min",
        "path": f"{SCORING_DIR}/scorers/d1_habitat_occupancy.py",
        "kind": "tuple",
        "args": {"const": "OCC_BAND", "path": (0,)},
    },
    {
        "name": "scoring.d1_band_max",
        "path": f"{SCORING_DIR}/scorers/d1_habitat_occupancy.py",
        "kind": "tuple",
        "args": {"const": "OCC_BAND", "path": (1,)},
    },
    {
        "name": "scoring.d1_center",
        "path": f"{SCORING_DIR}/scorers/d1_habitat_occupancy.py",
        "kind": "module",
        "args": {"const": "OCC_CENTER"},
    },
    {
        "name": "scoring.d1_sigma",
        "path": f"{SCORING_DIR}/scorers/d1_habitat_occupancy.py",
        "kind": "module",
        "args": {"const": "OCC_SIGMA"},
    },
    # --- scoring: D2 ----------------------------------------------------
    {
        "name": "scoring.d2_lifetime_centre",
        "path": f"{SCORING_DIR}/scorers/d2_survival.py",
        "kind": "line",
        "args": {"pattern": r"score = math\.exp\(-\(\(mean_life - ", "index": 0},
    },
    {
        "name": "scoring.d2_lifetime_width",
        "path": f"{SCORING_DIR}/scorers/d2_survival.py",
        "kind": "line",
        "args": {"pattern": r"score = math\.exp\(-\(\(mean_life - ", "index": 1},
    },
    {
        "name": "scoring.d2_window_min",
        "path": f"{SCORING_DIR}/scorers/d2_survival.py",
        "kind": "regex",
        "args": {"pattern": r'"(\d+)-\d+ days"', "group": 1, "cast": "int"},
    },
    {
        "name": "scoring.d2_window_max",
        "path": f"{SCORING_DIR}/scorers/d2_survival.py",
        "kind": "regex",
        "args": {"pattern": r'"\d+-(\d+) days"', "group": 1, "cast": "int"},
    },
    # --- scoring: D3 ----------------------------------------------------
    {
        "name": "scoring.d3_band_min",
        "path": f"{SCORING_DIR}/scorers/d3_eip.py",
        "kind": "line",
        "args": {"pattern": r"if 0\.\d+ <= eip_frac <= ", "index": 0},
    },
    {
        "name": "scoring.d3_band_max",
        "path": f"{SCORING_DIR}/scorers/d3_eip.py",
        "kind": "line",
        "args": {"pattern": r"if 0\.\d+ <= eip_frac <= ", "index": 1},
    },
    {
        "name": "scoring.d3_center",
        "path": f"{SCORING_DIR}/scorers/d3_eip.py",
        "kind": "line",
        "args": {"pattern": r"score = math\.exp\(-\(\(eip_frac - ", "index": 0},
    },
    {
        "name": "scoring.d3_sigma",
        "path": f"{SCORING_DIR}/scorers/d3_eip.py",
        "kind": "line",
        "args": {"pattern": r"score = math\.exp\(-\(\(eip_frac - ", "index": 1},
    },
    {
        "name": "scoring.d3_day",
        "path": f"{SCORING_DIR}/scorers/d3_eip.py",
        "kind": "line",
        "args": {"pattern": r"day30 = next\(\(e for e in daily if e\.get\(\"day\"\) == ", "index": 0},
    },
    # --- scoring: D4 ----------------------------------------------------
    {
        "name": "scoring.d4_collapse_min",
        "path": f"{SCORING_DIR}/scorers/d4_stability.py",
        "kind": "line",
        "args": {"pattern": r"if 0\.\d+ <= collapse_ratio <= ", "index": 0},
    },
    {
        "name": "scoring.d4_collapse_max",
        "path": f"{SCORING_DIR}/scorers/d4_stability.py",
        "kind": "line",
        "args": {"pattern": r"if 0\.\d+ <= collapse_ratio <= ", "index": 1},
    },
    {
        "name": "scoring.d4_explosion_max",
        "path": f"{SCORING_DIR}/scorers/d4_stability.py",
        "kind": "line",
        "args": {"pattern": r"if explosion_ratio <= ", "index": 0},
    },
    # --- scoring: D5 ----------------------------------------------------
    {
        "name": "scoring.d5_band_min",
        "path": f"{SCORING_DIR}/scorers/d5_morans.py",
        "kind": "line",
        "args": {"pattern": r"if 0\.\d+ <= i_value <= ", "index": 0},
    },
    {
        "name": "scoring.d5_band_max",
        "path": f"{SCORING_DIR}/scorers/d5_morans.py",
        "kind": "line",
        "args": {"pattern": r"if 0\.\d+ <= i_value <= ", "index": 1},
    },
    {
        "name": "scoring.d5_center",
        "path": f"{SCORING_DIR}/scorers/d5_morans.py",
        "kind": "line",
        "args": {"pattern": r"score = max\(0\.0, math\.exp\(-\(\(i_value - ", "index": 1},
    },
    {
        "name": "scoring.d5_sigma",
        "path": f"{SCORING_DIR}/scorers/d5_morans.py",
        "kind": "line",
        "args": {"pattern": r"score = max\(0\.0, math\.exp\(-\(\(i_value - ", "index": 2},
    },
    # --- scoring: D8 ----------------------------------------------------
    {
        "name": "scoring.d8_min_score",
        "path": f"{SCORING_DIR}/scorers/d8_coupling.py",
        "kind": "class",
        "args": {"cls": "CouplingScorer", "attr": "min_score"},
    },
    {
        "name": "scoring.d8_score_divisor",
        "path": f"{SCORING_DIR}/scorers/d8_coupling.py",
        "kind": "line",
        "args": {"pattern": r"score = max\(0\.0, min\(1\.0, r / ", "index": 2},
    },
    {
        "name": "scoring.d8_pass_threshold",
        "path": f"{SCORING_DIR}/scorers/d8_coupling.py",
        "kind": "line",
        "args": {"pattern": r"passed=r >= ", "index": 0},
    },
    # --- scoring: D11 ---------------------------------------------------
    {
        "name": "scoring.d11_larva_band_min",
        "path": f"{SCORING_DIR}/scorers/d11_aquatic_structure.py",
        "kind": "tuple",
        "args": {"const": "LARVA_BAND", "path": (0,)},
    },
    {
        "name": "scoring.d11_larva_band_max",
        "path": f"{SCORING_DIR}/scorers/d11_aquatic_structure.py",
        "kind": "tuple",
        "args": {"const": "LARVA_BAND", "path": (1,)},
    },
    {
        "name": "scoring.d11_pupa_band_min",
        "path": f"{SCORING_DIR}/scorers/d11_aquatic_structure.py",
        "kind": "tuple",
        "args": {"const": "PUPA_BAND", "path": (0,)},
    },
    {
        "name": "scoring.d11_pupa_band_max",
        "path": f"{SCORING_DIR}/scorers/d11_aquatic_structure.py",
        "kind": "tuple",
        "args": {"const": "PUPA_BAND", "path": (1,)},
    },
    # --- scoring: D15 ---------------------------------------------------
    {
        "name": "scoring.d15_survival_fraction",
        "path": f"{SCORING_DIR}/scorers/d15_persistence.py",
        "kind": "line",
        "args": {"pattern": r"survival = min\(pop_last / max_pop / ", "index": 0},
    },
    {
        "name": "scoring.d15_expansion_fraction",
        "path": f"{SCORING_DIR}/scorers/d15_persistence.py",
        "kind": "line",
        "args": {"pattern": r"expansion = min\(\(cells_last / cells_base\) / ", "index": 0},
    },
    {
        "name": "scoring.d15_min_horizon_days",
        "path": f"{SCORING_DIR}/scorers/d15_persistence.py",
        "kind": "line",
        "args": {"pattern": r"if last_day < ", "index": 0},
    },
    # --- scoring: D16 ---------------------------------------------------
    {
        "name": "scoring.d16_coverage_target",
        "path": f"{SCORING_DIR}/scorers/d16_detection_coverage.py",
        "kind": "module",
        "args": {"const": "COVERAGE_TARGET"},
    },
    {
        "name": "scoring.d16_radius_km_default",
        "path": f"{SCORING_DIR}/scorers/d16_detection_coverage.py",
        "kind": "module",
        "args": {"const": "RADIUS_KM_DEFAULT"},
    },
    {
        "name": "scoring.d16_sensitivity_radius_near_km",
        "path": f"{SCORING_DIR}/scorers/d16_detection_coverage.py",
        "kind": "tuple",
        "args": {"const": "SENSITIVITY_RADII_KM", "path": (0,)},
    },
    {
        "name": "scoring.d16_sensitivity_radius_mid_km",
        "path": f"{SCORING_DIR}/scorers/d16_detection_coverage.py",
        "kind": "tuple",
        "args": {"const": "SENSITIVITY_RADII_KM", "path": (1,)},
    },
    {
        "name": "scoring.d16_sensitivity_radius_far_km",
        "path": f"{SCORING_DIR}/scorers/d16_detection_coverage.py",
        "kind": "tuple",
        "args": {"const": "SENSITIVITY_RADII_KM", "path": (2,)},
    },
    # --- scoring: D19 ---------------------------------------------------
    {
        "name": "scoring.d19_activation_floor",
        "path": f"{SCORING_DIR}/scorers/d19_pool_persistence.py",
        "kind": "line",
        "args": {"pattern": r"if z >= ", "index": 0},
    },
    {
        "name": "scoring.d19_rain_pulse_mm",
        "path": f"{SCORING_DIR}/scorers/d19_pool_persistence.py",
        "kind": "line",
        "args": {"pattern": r"z = step\(z, ", "index": 0},
    },
    {
        "name": "scoring.d19_pulse_days",
        "path": f"{SCORING_DIR}/scorers/d19_pool_persistence.py",
        "kind": "line",
        "args": {"pattern": r"for _ in range\(", "index": 0},
    },
    {
        "name": "scoring.d19_dry_days",
        "path": f"{SCORING_DIR}/scorers/d19_pool_persistence.py",
        "kind": "line",
        "args": {"pattern": r"for d in range\(", "index": 0},
    },
    {
        "name": "scoring.d19_check_persistence_weight",
        "path": f"{SCORING_DIR}/scorers/d19_pool_persistence.py",
        "kind": "after",
        "args": {"pattern": r"if persistence_ok:", "index": 0},
    },
    {
        "name": "scoring.d19_check_drying_weight",
        "path": f"{SCORING_DIR}/scorers/d19_pool_persistence.py",
        "kind": "after",
        "args": {"pattern": r"if dries_out:", "index": 0},
    },
    {
        "name": "scoring.d19_check_monotone_weight",
        "path": f"{SCORING_DIR}/scorers/d19_pool_persistence.py",
        "kind": "after",
        "args": {"pattern": r"if monotone:", "index": 0},
    },
    {
        "name": "scoring.d19_check_floor_weight",
        "path": f"{SCORING_DIR}/scorers/d19_pool_persistence.py",
        "kind": "after",
        "args": {"pattern": r"if floor_ok:", "index": 0},
    },
    # --- scoring: D20 ---------------------------------------------------
    {
        "name": "scoring.d20_no_washout_probe_mm",
        "path": f"{SCORING_DIR}/scorers/d20_washout_response.py",
        "kind": "line",
        "args": {"pattern": r"frac_30 = washout_fraction\(", "index": 0},
    },
    {
        "name": "scoring.d20_threshold_probe_mm",
        "path": f"{SCORING_DIR}/scorers/d20_washout_response.py",
        "kind": "line",
        "args": {"pattern": r"frac_40 = washout_fraction\(", "index": 0},
    },
    {
        "name": "scoring.d20_washout_probe_mm",
        "path": f"{SCORING_DIR}/scorers/d20_washout_response.py",
        "kind": "line",
        "args": {"pattern": r"frac_50 = washout_fraction\(", "index": 0},
    },
    {
        "name": "scoring.d20_cap_probe_mm",
        "path": f"{SCORING_DIR}/scorers/d20_washout_response.py",
        "kind": "line",
        "args": {"pattern": r"frac_80 = washout_fraction\(", "index": 0},
    },
    {
        "name": "scoring.d20_min_washout_fraction",
        "path": f"{SCORING_DIR}/scorers/d20_washout_response.py",
        "kind": "line",
        "args": {"pattern": r"test1_ok = frac_50 >= ", "index": 0},
    },
    {
        "name": "scoring.d20_threshold_max_fraction",
        "path": f"{SCORING_DIR}/scorers/d20_washout_response.py",
        "kind": "line",
        "args": {"pattern": r"test4_ok = frac_40 <= ", "index": 0},
    },
    {
        "name": "scoring.d20_check_washout_weight",
        "path": f"{SCORING_DIR}/scorers/d20_washout_response.py",
        "kind": "after",
        "args": {"pattern": r"if test1_ok:", "index": 0},
    },
    {
        "name": "scoring.d20_check_no_washout_weight",
        "path": f"{SCORING_DIR}/scorers/d20_washout_response.py",
        "kind": "after",
        "args": {"pattern": r"if test2_ok:", "index": 0},
    },
    {
        "name": "scoring.d20_check_cap_weight",
        "path": f"{SCORING_DIR}/scorers/d20_washout_response.py",
        "kind": "after",
        "args": {"pattern": r"if test3_ok:", "index": 0},
    },
    {
        "name": "scoring.d20_check_threshold_weight",
        "path": f"{SCORING_DIR}/scorers/d20_washout_response.py",
        "kind": "after",
        "args": {"pattern": r"if test4_ok:", "index": 0},
    },
    # --- scoring: D21 ---------------------------------------------------
    {
        "name": "scoring.d21_p50_band_min",
        "path": f"{SCORING_DIR}/scorers/d21_dispersal_kernel.py",
        "kind": "tuple",
        "args": {"const": "P50_BAND", "path": (0,)},
    },
    {
        "name": "scoring.d21_p50_band_max",
        "path": f"{SCORING_DIR}/scorers/d21_dispersal_kernel.py",
        "kind": "tuple",
        "args": {"const": "P50_BAND", "path": (1,)},
    },
    {
        "name": "scoring.d21_p90_band_min",
        "path": f"{SCORING_DIR}/scorers/d21_dispersal_kernel.py",
        "kind": "tuple",
        "args": {"const": "P90_BAND", "path": (0,)},
    },
    {
        "name": "scoring.d21_p90_band_max",
        "path": f"{SCORING_DIR}/scorers/d21_dispersal_kernel.py",
        "kind": "tuple",
        "args": {"const": "P90_BAND", "path": (1,)},
    },
    {
        "name": "scoring.d21_p50_center",
        "path": f"{SCORING_DIR}/scorers/d21_dispersal_kernel.py",
        "kind": "module",
        "args": {"const": "P50_CENTER"},
    },
    {
        "name": "scoring.d21_p50_sigma",
        "path": f"{SCORING_DIR}/scorers/d21_dispersal_kernel.py",
        "kind": "module",
        "args": {"const": "P50_SIGMA"},
    },
    {
        "name": "scoring.d21_p90_center",
        "path": f"{SCORING_DIR}/scorers/d21_dispersal_kernel.py",
        "kind": "module",
        "args": {"const": "P90_CENTER"},
    },
    {
        "name": "scoring.d21_p90_sigma",
        "path": f"{SCORING_DIR}/scorers/d21_dispersal_kernel.py",
        "kind": "module",
        "args": {"const": "P90_SIGMA"},
    },
    {
        "name": "scoring.d21_horizon_day",
        "path": f"{SCORING_DIR}/scorers/d21_dispersal_kernel.py",
        "kind": "line",
        "args": {"pattern": r"horizon = max\(\(d for d in day_files if d <= ", "index": 0},
    },
    # --- scoring: D25 ---------------------------------------------------
    {
        "name": "scoring.d25_r_target",
        "path": f"{SCORING_DIR}/scorers/d25_cases_ghana.py",
        "kind": "module",
        "args": {"const": "R_TARGET"},
    },
    # --- scoring: the gates ---------------------------------------------
    {
        "name": "scoring.gate_sample_files",
        "path": f"{SCORING_DIR}/scorers/gates.py",
        "kind": "line",
        "args": {"pattern": r"tifs = \[tifs\[int\(i \* step\)\] for i in range\(", "index": 0},
    },
    {
        "name": "scoring.gate_wall_time_limit_s",
        "path": f"{SCORING_DIR}/scorers/gates.py",
        "kind": "line",
        "args": {"pattern": r"passed=wall_s <= ", "index": 0},
    },
    {
        "name": "scoring.gate_census_reference",
        "path": f"{SCORING_DIR}/scorers/gates.py",
        "kind": "line",
        "args": {"pattern": r"ref_total = float\(ctx\.get\(\"human_reference_total\", ", "index": 0},
    },
    {
        "name": "scoring.gate_ratio_band_min",
        "path": f"{SCORING_DIR}/scorers/gates.py",
        "kind": "line",
        "args": {"pattern": r"passed=0\.\d+ <= ratio <= ", "index": 0},
    },
    {
        "name": "scoring.gate_ratio_band_max",
        "path": f"{SCORING_DIR}/scorers/gates.py",
        "kind": "line",
        "args": {"pattern": r"passed=0\.\d+ <= ratio <= ", "index": 1},
    },
    {
        "name": "scoring.gate_row_sum_tolerance",
        "path": f"{SCORING_DIR}/scorers/gates.py",
        "kind": "line",
        "args": {"pattern": r"\(np\.abs\(sums - 1\.0\) < ", "index": 1},
    },
    {
        "name": "scoring.gate_row_sum_threshold",
        "path": f"{SCORING_DIR}/scorers/gates.py",
        "kind": "line",
        "args": {"pattern": r"passed=min_fraction >= ", "index": 0},
    },
    {
        "name": "scoring.gate_urban_class",
        "path": f"{SCORING_DIR}/scorers/gates.py",
        "kind": "line",
        "args": {"pattern": r"urban_mask = mask_d & \(urban_class == ", "index": 0},
    },
    {
        "name": "scoring.gate_rural_class",
        "path": f"{SCORING_DIR}/scorers/gates.py",
        "kind": "line",
        "args": {"pattern": r"rural_mask = mask_d & \(urban_class == ", "index": 0},
    },
    {
        "name": "scoring.gate_urban_ratio_max",
        "path": f"{SCORING_DIR}/scorers/gates.py",
        "kind": "line",
        "args": {"pattern": r"passed=ratio <= ", "index": 0},
    },
    # --- ingest ----------------------------------------------------------
    {
        "name": "ingest.cell_size_m",
        "path": "mal-commonlib/src/mal_commonlib/aois.yaml",
        "kind": "aoi",
        "args": {"aoi": "ghana", "field": "resolution_m"},
    },
    {
        "name": "ingest.bbox_west",
        "path": "mal-commonlib/src/mal_commonlib/aois.yaml",
        "kind": "aoi",
        "args": {"aoi": "ghana", "field": "bbox_west"},
    },
    {
        "name": "ingest.bbox_south",
        "path": "mal-commonlib/src/mal_commonlib/aois.yaml",
        "kind": "aoi",
        "args": {"aoi": "ghana", "field": "bbox_south"},
    },
    {
        "name": "ingest.bbox_east",
        "path": "mal-commonlib/src/mal_commonlib/aois.yaml",
        "kind": "aoi",
        "args": {"aoi": "ghana", "field": "bbox_east"},
    },
    {
        "name": "ingest.bbox_north",
        "path": "mal-commonlib/src/mal_commonlib/aois.yaml",
        "kind": "aoi",
        "args": {"aoi": "ghana", "field": "bbox_north"},
    },
    {
        "name": "ingest.jrc_occurrence_threshold_pct",
        "path": f"{LOADERS_DIR}/jrc_gsw.py",
        "kind": "module",
        "args": {"const": "DEFAULT_THRESHOLD_PCT"},
    },
    {
        "name": "ingest.env_daily_channels",
        "path": f"{INGEST_DIR}/daily_nc.py",
        "kind": "envcounts",
        "args": {"which": "daily"},
    },
    {
        "name": "ingest.env_static_planes",
        "path": f"{INGEST_DIR}/daily_nc.py",
        "kind": "envcounts",
        "args": {"which": "static"},
    },
    {
        "name": "ingest.fallback_building_urban",
        "path": f"{INGEST_DIR}/hosts.py",
        "kind": "line",
        "args": {"pattern": r"building_frac = np\.where\(urban_class == ", "index": 1},
    },
    {
        "name": "ingest.fallback_building_rural",
        "path": f"{INGEST_DIR}/hosts.py",
        "kind": "line",
        "args": {"pattern": r"building_frac = np\.where\(urban_class == ", "index": 2},
    },
    {
        "name": "ingest.fallback_wildlife_proxy",
        "path": f"{INGEST_DIR}/hosts.py",
        "kind": "line",
        "args": {"pattern": r"wildlife_proxy = np\.full\(\(h, w\), ", "index": 0},
    },
    {
        "name": "ingest.urban_class_urban",
        "path": f"{INGEST_DIR}/hosts.py",
        "kind": "line",
        "args": {"pattern": r"reclassified = np\.where\(urban_class == ", "index": 0},
    },
    {
        "name": "ingest.urban_class_rural",
        "path": f"{INGEST_DIR}/hosts.py",
        "kind": "line",
        "args": {"pattern": r"\(urban_class >= 20\) & \(urban_class < 30\), 50,", "index": 2},
    },
    {
        "name": "ingest.urban_class_water",
        "path": f"{INGEST_DIR}/hosts.py",
        "kind": "line",
        "args": {"pattern": r"\(urban_class < 20\), 20, 50\)", "index": 1},
    },
    {
        "name": "ingest.mobility_cell_size_km",
        "path": f"{INGEST_DIR}/mobility.py",
        "kind": "default",
        "args": {"qualname": "build_mobility_dataset", "arg": "cell_size_km"},
    },
    {
        "name": "ingest.mobility_beta_day",
        "path": f"{INGEST_DIR}/mobility.py",
        "kind": "default",
        "args": {"qualname": "build_mobility_dataset", "arg": "beta_day"},
    },
    {
        "name": "ingest.mobility_beta_night",
        "path": f"{INGEST_DIR}/mobility.py",
        "kind": "default",
        "args": {"qualname": "build_mobility_dataset", "arg": "beta_night"},
    },
    {
        "name": "ingest.mobility_beta_livestock",
        "path": f"{INGEST_DIR}/mobility.py",
        "kind": "default",
        "args": {"qualname": "build_mobility_dataset", "arg": "beta_livestock"},
    },
    {
        "name": "ingest.mobility_max_distance_km",
        "path": f"{INGEST_DIR}/mobility.py",
        "kind": "default",
        "args": {"qualname": "build_mobility_dataset", "arg": "max_distance_km"},
    },
    {
        "name": "ingest.mobility_sparsity_threshold",
        "path": f"{INGEST_DIR}/mobility.py",
        "kind": "default",
        "args": {"qualname": "build_mobility_dataset", "arg": "sparsity_threshold"},
    },
    {
        "name": "ingest.k_ref_diag_per_km2",
        "path": f"{HABITAT_DIR}/capacity.py",
        "kind": "module",
        "args": {"const": "K_REF_DIAG_PER_KM2"},
    },
    # --- download --------------------------------------------------------
    {
        "name": "download.wildlife_habitat_fallback",
        "path": f"{LOADERS_DIR}/wildlife.py",
        "kind": "line",
        "args": {"pattern": r"habitat = np\.full\(\(H, W\), ", "index": 0},
    },
    {
        "name": "download.wildlife_remoteness_neutral",
        "path": f"{LOADERS_DIR}/wildlife.py",
        "kind": "line",
        "args": {"pattern": r"score\[nodata\] = 1\.0", "index": 0},
    },
)


def _env_counts(path: str, which: str) -> tuple[int, int]:
    """Count the env NC's daily variables and its static planes.

    The NC is assembled as one ``xr.Dataset({...})`` literal; a variable
    whose dims carry ``time`` is a daily channel, the others are static
    planes. Counting the dataset's own keys is the code's count.
    """
    tree = _tree(path)
    dataset: ast.Dict | None = None
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
            func = node.value.func
            if isinstance(func, ast.Attribute) and func.attr == "Dataset":
                if node.value.args and isinstance(node.value.args[0], ast.Dict):
                    dataset = node.value.args[0]
    if dataset is None:
        _fail(f"{path}: no xr.Dataset({...}) literal found")
    daily = 0
    static = 0
    for key, value in zip(dataset.keys, dataset.values):
        if not (isinstance(key, ast.Constant) and isinstance(key.value, str)):
            continue
        dims: list[str] = []
        if isinstance(value, ast.Tuple) and value.elts:
            first = value.elts[0]
            if isinstance(first, (ast.List, ast.Tuple)):
                dims = [
                    element.value
                    for element in first.elts
                    if isinstance(element, ast.Constant)
                ]
        if "time" in dims:
            daily += 1
        else:
            static += 1
    return daily, static


def _scale_grid(path: str, scale: str) -> tuple[Any, int]:
    """The resolution of one scale's GridDef, and the line it is written on."""
    tree = _tree(path)
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        if not any(isinstance(t, ast.Name) and t.id == "SCALE_GRIDS" for t in targets):
            continue
        if not isinstance(node.value, ast.Dict):
            continue
        for key, value in zip(node.value.keys, node.value.values):
            if not isinstance(key, ast.Attribute):
                continue
            if key.attr != scale:
                continue
            if not isinstance(value, ast.Call) or not value.args:
                continue
            return _value_of(value.args[0]), value.args[0].lineno
    _fail(f"{path}: no SCALE_GRIDS entry for Scale.{scale}")
    raise  # unreachable


def _aoi_field(aoi: str, field: str) -> tuple[Any, int]:
    """One field of the AOI registry, and the line it is written on."""
    from mal_commonlib.aoi import _load_aois_yaml

    payload = _load_aois_yaml().get(aoi)
    if payload is None:
        _fail(f"aois.yaml has no AOI {aoi!r}")
    lines = _text("mal-commonlib/src/mal_commonlib/aois.yaml").splitlines()
    if field in ("bbox_west", "bbox_south", "bbox_east", "bbox_north"):
        index = ("bbox_west", "bbox_south", "bbox_east", "bbox_north").index(field)
        bbox = payload.get("bbox")
        if not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
            _fail(f"aois.yaml AOI {aoi!r} has no four-element bbox")
        for lineno, line in enumerate(lines, start=1):
            if re.match(rf"^\s*bbox:\s*\[", line) and str(bbox) in line.replace(" ", ""):
                return float(bbox[index]), lineno
        for lineno, line in enumerate(lines, start=1):
            if re.match(rf"^\s*bbox:\s*\[", line):
                return float(bbox[index]), lineno
        _fail(f"aois.yaml: no bbox line for AOI {aoi!r}")
    for lineno, line in enumerate(lines, start=1):
        if re.match(rf"^\s*{re.escape(field)}:\s*", line):
            return payload.get(field), lineno
    _fail(f"aois.yaml: no {field!r} line for AOI {aoi!r}")
    raise  # unreachable


def _read_code_value(spec: dict[str, Any]) -> CodeValue:
    """Read one value, by the kind the specification names."""
    path = spec["path"]
    args = spec.get("args", {})
    kind = spec["kind"]
    if kind == "module":
        bindings = _module_bindings(path)
        name = args["const"]
        if name not in bindings:
            _fail(f"{path}: module constant {name!r} not found")
        value, lineno = bindings[name]
        return CodeValue(value, f"{path}:{lineno}")
    if kind == "class":
        bindings = _class_bindings(path)
        key = (args["cls"], args["attr"])
        if key not in bindings:
            _fail(f"{path}: class attribute {key[0]}.{key[1]} not found")
        value, lineno = bindings[key]
        return CodeValue(value, f"{path}:{lineno}")
    if kind == "default":
        defaults = _defaults(path, args["qualname"])
        name = args["arg"]
        if name not in defaults:
            _fail(f"{path}: {args['qualname']} has no default {name!r}")
        value, lineno = defaults[name]
        return CodeValue(value, f"{path}:{lineno}")
    if kind == "tuple":
        bindings = _module_bindings(path)
        name = args["const"]
        if name not in bindings:
            _fail(f"{path}: module constant {name!r} not found")
        value = bindings[name][0]
        for step in args["path"]:
            if not isinstance(value, (tuple, list)) or step >= len(value):
                _fail(f"{path}: {name} has no element {args['path']}")
            value = value[step]
        lineno = bindings[name][1]
        return CodeValue(value, f"{path}:{lineno}")
    if kind == "line":
        occurrence = args.get("occurrence", 0)
        lineno = _match_line(path, args["pattern"], occurrence)
        want = args.get("want", "num")
        values = _line_literals(path, lineno, want)
        value = _select(values, args.get("index", 0), path, args["pattern"])
        return CodeValue(value, f"{path}:{lineno}")
    if kind == "after":
        occurrence = args.get("occurrence", 0)
        lineno = _match_line(path, args["pattern"], occurrence)
        lines = _text(path).splitlines()
        target = None
        for offset in range(1, len(lines) - lineno + 1):
            candidate = lines[lineno - 1 + offset]
            if candidate.strip():
                target = lineno + offset
                break
        if target is None:
            _fail(f"{path}: no line follows {args['pattern']!r}")
        want = args.get("want", "num")
        values = _line_literals(path, target, want)
        value = _select(values, args.get("index", 0), path, args["pattern"])
        return CodeValue(value, f"{path}:{target}")
    if kind == "regex":
        pattern = args["pattern"]
        where = args.get("where", "text")
        if where == "docstring":
            doc = ast.get_docstring(_tree(path)) or ""
            haystack = doc
        else:
            haystack = _text(path)
        matches = list(re.finditer(pattern, haystack))
        occurrence = args.get("occurrence", 0)
        if occurrence >= len(matches):
            _fail(f"{path}: pattern {pattern!r} matched {len(matches)} times")
        match = matches[occurrence]
        captured = match.group(args["group"])
        cast = args.get("cast", "str")
        if cast == "int":
            value: Any = int(captured)
        elif cast == "float":
            value = float(captured)
        else:
            value = captured
        lineno = _text(path).count("\n", 0, match.start()) + 1
        return CodeValue(value, f"{path}:{lineno}")
    if kind == "scale":
        value, lineno = _scale_grid(path, args["scale"])
        return CodeValue(value, f"{path}:{lineno}")
    if kind == "envcounts":
        daily, static = _env_counts(path, args["which"])
        value = daily if args["which"] == "daily" else static
        lineno = _env_counts_line(path)
        return CodeValue(value, f"{path}:{lineno}")
    if kind == "aoi":
        value, lineno = _aoi_field(args["aoi"], args["field"])
        return CodeValue(value, f"{path}:{lineno}")
    _fail(f"unknown spec kind {kind!r} for {spec['name']!r}")
    raise  # unreachable


def _env_counts_line(path: str) -> int:
    for node in ast.walk(_tree(path)):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
            func = node.value.func
            if isinstance(func, ast.Attribute) and func.attr == "Dataset":
                return node.lineno
    return 1


def build_code_values() -> dict[str, CodeValue]:
    """Every code constant the documents may cite, with its provenance."""
    values: dict[str, CodeValue] = {}
    for spec in CODE_SPECS:
        name = spec["name"]
        if name in values:
            _fail(f"duplicate code constant {name!r}")
        values[name] = _read_code_value(spec)
    return values


def _format_code_value(value: Any) -> str:
    if isinstance(value, (tuple, list)):
        return ", ".join(str(item) for item in value)
    return format_value(value)


def emit_code_macros(values: dict[str, CodeValue]) -> str:
    """The second macro family: ``\\codeconst{<stage>.<name>}``."""
    out = [
        "% Generated by tools/gen_concepts_values.py -- do not edit.",
        "% Values are read from the CODE that implements each stage, by AST.",
        "% A key that no longer exists makes \\codeconst fail the LaTeX build",
        "% with an error, in any document that references it.",
        "% Each line carries the file:line the value was read from.",
        "",
        "\\makeatletter",
        "\\newcommand{\\codeconst}[1]{%",
        "  \\expandafter\\ifx\\csname cc@k@#1\\endcsname\\relax",
        "    \\errmessage{Concept document: unknown code constant `#1'}%",
        "  \\else",
        "    \\csname cc@k@#1\\endcsname%",
        "  \\fi}",
        "\\makeatother",
        "",
    ]
    for name in sorted(values):
        item = values[name]
        out.append(
            f"% {name} = {_format_code_value(item.value)}  ({item.source})"
        )
        out.append(
            f"\\expandafter\\def\\csname cc@k@{name}\\endcsname"
            f"{{{latex_escape(_format_code_value(item.value))}}}"
        )
    out.append("")
    return "\n".join(out)


# ---------------------------------------------------------------------------
# The loaders' native grids.
#
# A loader states its native grid either as a constant or in its own
# docstring. Both are read; a value that exists in neither leaves the cell
# EMPTY rather than being typed here.
# ---------------------------------------------------------------------------

LOADER_GRID_SPECS: tuple[dict[str, Any], ...] = (
    {
        "loader": "buildings",
        "module": "buildings.py",
        "grid": [],
        "epoch": [],
    },
    {
        "loader": "chirps",
        "module": "chirps.py",
        "grid": [
            {
                "kind": "regex",
                "where": "docstring",
                "pattern": r"GeoTIFFs at (0\.05° \(~5 km\)) resolution",
                "group": 1,
            }
        ],
        "epoch": [
            {
                "kind": "regex",
                "where": "docstring",
                "pattern": r"CHIRPS (v2\.0) daily precipitation loader",
                "group": 1,
            },
            {
                "kind": "regex",
                "where": "text",
                "pattern": r"CHIRPS starts in (\d{4})",
                "group": 1,
                "prefix": "from ",
            },
        ],
    },
    {
        "loader": "coastline",
        "module": "coastline.py",
        "grid": [],
        "epoch": [
            {"kind": "module", "const": "_GSHHG_VERSION"},
        ],
    },
    {
        "loader": "dynamic_world",
        "module": "dynamic_world.py",
        "grid": [
            {
                "kind": "regex",
                "where": "text",
                "pattern": r"Dynamic World is (10 m)",
                "group": 1,
                "prefix": "native: ",
            },
            {
                "kind": "module",
                "const": "_REQUEST_SCALE_M",
                "suffix": " m (request scale)",
            },
        ],
        "epoch": [
            {"kind": "module", "const": "_EE_COLLECTION"},
        ],
    },
    {
        "loader": "era5",
        "module": "era5.py",
        "grid": [
            {
                "kind": "regex",
                "where": "text",
                "pattern": r"source grid is (0\.1 deg)",
                "group": 1,
            }
        ],
        "epoch": [
            {
                "kind": "regex",
                "where": "docstring",
                "pattern": r"``(derived-era5-land-daily-statistics)`` dataset",
                "group": 1,
            }
        ],
    },
    {
        "loader": "ghsl",
        "module": "ghsl.py",
        "grid": [
            {
                "kind": "regex",
                "where": "docstring",
                "pattern": r"\(Mollweide (~1 km), 2030 epoch\)",
                "group": 1,
            }
        ],
        "epoch": [
            {
                "kind": "regex",
                "where": "docstring",
                "pattern": r"Product: (GHS_SMOD_E2030_GLOBE_R2023A)",
                "group": 1,
            }
        ],
    },
    {
        "loader": "glw",
        "module": "glw.py",
        "grid": [
            {
                "kind": "regex",
                "where": "docstring",
                "pattern": r"density \((~10 km, ~5 arc-minutes)\)",
                "group": 1,
            }
        ],
        "epoch": [
            {
                "kind": "regex",
                "where": "docstring",
                "pattern": r"Downloads (GLW4 2020) livestock",
                "group": 1,
            }
        ],
    },
    {
        "loader": "jrc_gsw",
        "module": "jrc_gsw.py",
        "grid": [
            {
                "kind": "regex",
                "where": "docstring",
                "pattern": r"\(GSW\) (30 m) static habitat loader",
                "group": 1,
            }
        ],
        "epoch": [
            {
                "kind": "regex",
                "where": "text",
                "pattern": r"occurrence (\d{4}-\d{4})",
                "group": 1,
            }
        ],
    },
    {
        "loader": "modis",
        "module": "modis.py",
        "grid": [
            {
                "kind": "regex",
                "where": "docstring",
                "pattern": r"Global (1 km) SIN",
                "group": 1,
            }
        ],
        "epoch": [
            {
                "kind": "regex",
                "where": "docstring",
                "pattern": r"MODIS MOD13A3 (v061)",
                "group": 1,
            }
        ],
    },
    {
        "loader": "smap",
        "module": "smap.py",
        "grid": [
            {"kind": "module", "const": "_GRID_STEP", "suffix": "\u00b0"},
        ],
        "epoch": [
            {"kind": "module", "const": "_DATASET_ID"},
        ],
    },
    {
        "loader": "wildlife",
        "module": "wildlife.py",
        "grid": [],
        "epoch": [],
    },
    {
        "loader": "worldpop",
        "module": "worldpop.py",
        "grid": [
            {
                "kind": "regex",
                "where": "docstring",
                "pattern": r"source raster \((~100 m)\)",
                "group": 1,
            }
        ],
        "epoch": [
            {
                "kind": "regex",
                "where": "docstring",
                "pattern": r"legacy \"(Global1)\" (2000–2020)",
                "group": 1,
            },
            {
                "kind": "regex",
                "where": "docstring",
                "pattern": r"legacy \"Global1\" (2000–2020)",
                "group": 1,
            },
        ],
    },
)


def _loader_part(path: str, spec: dict[str, Any]) -> str:
    """One cell of the loader table: the text, or "" when unstated."""
    kind = spec["kind"]
    if kind == "module":
        bindings = _module_bindings(path)
        name = spec["const"]
        if name not in bindings:
            _fail(f"{path}: module constant {name!r} not found")
        value = bindings[name][0]
        if isinstance(value, float) and value.is_integer():
            text = f"{value:g}"
        else:
            text = str(value)
    elif kind == "regex":
        where = spec.get("where", "text")
        haystack = (
            (ast.get_docstring(_tree(path)) or "") if where == "docstring" else _text(path)
        )
        matches = list(re.finditer(spec["pattern"], haystack))
        if not matches:
            _fail(f"{path}: pattern {spec['pattern']!r} matched nothing")
        text = matches[0].group(spec["group"])
    else:
        _fail(f"unknown loader cell kind {kind!r}")
        raise  # unreachable
    prefix = spec.get("prefix", "")
    suffix = spec.get("suffix", "")
    return f"{prefix}{text}{suffix}"


def emit_loader_grid_table() -> str:
    """One row per loader: the product's native grid and its epoch."""
    out = [
        "% Generated by tools/gen_concepts_values.py -- do not edit.",
        "\\paragraph{The loaders' native grids (the resolution each product "
        "is published at)}",
        "\\begin{longtable}{@{}llll@{}}",
        "\\toprule",
        "Loader & Native grid & Product / epoch & Source \\\\",
        "\\midrule",
        "\\endhead",
    ]
    for spec in LOADER_GRID_SPECS:
        path = f"{LOADERS_DIR}/{spec['module']}"
        grid = " / ".join(_loader_part(path, part) for part in spec["grid"])
        epoch = " / ".join(_loader_part(path, part) for part in spec["epoch"])
        grid_cell = grid if grid else "---"
        epoch_cell = epoch if epoch else "---"
        out.append(
            f"\\code{{{latex_escape(spec['loader'])}}} & "
            f"{latex_escape(grid_cell)} & {latex_escape(epoch_cell)} & "
            f"\\code{{{latex_escape(spec['module'])}}} \\\\"
        )
    out.append("\\bottomrule")
    out.append("\\end{longtable}")
    out.append(
        "\\noindent\\emph{---}: the loader's code states no such value; the "
        "cell is left empty rather than typed by hand.",
    )
    out.append("")
    return "\n".join(out)


# --- scenario harness catalogue ---------------------------------------------

SCENARIO_DIR = (
    REPO / "mal-core" / "src" / "mal_core" / "abm" / "tests" / "scenarios"
)
_SCENARIO_FIELDS = (
    "title", "purpose", "setup", "implies", "expected", "closes",
    "executable_today", "today", "verified_now", "gif",
)


def _scenario_facts(spec: dict[str, Any]) -> list[tuple[str, str]]:
    """Facts that are read from the scenario JSON, never typed in prose."""
    import math

    agents = spec.get("agents", [])
    n_f = sum(1 for a in agents if a.get("sex") == "FEMALE")
    n_m = sum(1 for a in agents if a.get("sex") == "MALE")
    facts = [
        ("Mode", spec["mode"]),
        ("Seed / days", f"{spec['seed']} / {spec['days']}"),
        ("Mosquitoes seeded", f"{n_f} female, {n_m} male"),
    ]
    if spec.get("aquatic"):
        facts.append((
            "Aquatic cohorts",
            "; ".join(
                f"{c['count']} {c['stage']} at ({c['x']:g}, {c['y']:g}) m"
                for c in spec["aquatic"]),
        ))
    humans = spec.get("humans", [])
    if humans and agents:
        a0 = agents[0]
        dist = ", ".join(
            f"{math.hypot(h['x'] - a0['x'], h['y'] - a0['y']):.0f} m"
            for h in humans[:6]
        )
        more = "" if len(humans) <= 6 else f" (+{len(humans) - 6} more)"
        facts.append((
            "People",
            f"{len(humans)}; distance from the first mosquito: {dist}{more}",
        ))
    if spec.get("livestock"):
        facts.append(("Livestock", str(len(spec["livestock"]))))
    variants = spec.get("variants") or []
    if variants:
        facts.append(("Variants", ", ".join(v.get("label", "?") for v in variants)))
    keys = sorted(
        {k for v in [spec] + list(variants) for k in (v.get("overrides") or {})}
    )
    if keys:
        facts.append(("Overrides", ", ".join(keys)))
    return facts


def emit_scenarios() -> str:
    """The scenario catalogue as an appendix fragment of the ABM document.

    Prose comes from ``catalog.yaml`` (hand-written semantics); every number
    the scenario fixes comes from its JSON, so the two cannot drift apart:
    a scenario without a catalogue entry (or the reverse) fails the build.
    """
    import json

    import yaml

    catalog = yaml.safe_load((SCENARIO_DIR / "catalog.yaml").read_text())
    ids = sorted(p.stem for p in SCENARIO_DIR.glob("E[0-9][0-9].json"))
    if sorted(catalog) != ids:
        _fail(
            "scenario catalogue and scenario files disagree: "
            f"only in catalog {sorted(set(catalog) - set(ids))}, "
            f"only in files {sorted(set(ids) - set(catalog))}"
        )
    esc = latex_escape
    out = ["% Generated by tools/gen_concepts_values.py -- do not edit."]
    for sid in ids:
        entry = catalog[sid]
        missing = [f for f in _SCENARIO_FIELDS if not str(entry.get(f, "")).strip()]
        if missing:
            _fail(f"scenario catalogue {sid}: empty or missing fields {missing}")
        spec = json.loads((SCENARIO_DIR / f"{sid}.json").read_text())
        out.append(f"\\subsection*{{{sid} --- {esc(str(entry['title']))}}}")
        out.append("\\begin{tabular}{@{}ll@{}}")
        for k, v in _scenario_facts(spec):
            out.append(f"\\textit{{{esc(k)}}} & {esc(v)} \\\\")
        out.append(
            f"\\textit{{Closes}} & {esc(str(entry['closes']))} \\\\"
        )
        out.append(
            f"\\textit{{Runs a behaviour test today}} & "
            f"{esc(str(entry['executable_today']))} \\\\"
        )
        out.append("\\end{tabular}")
        out.append("")
        for label, key in (
            ("Purpose.", "purpose"),
            ("Setup.", "setup"),
            ("What passing or failing implies.", "implies"),
            ("Expected behaviour.", "expected"),
            ("What the current chain does.", "today"),
        ):
            out.append(f"\\par\\smallskip\\noindent\\textbf{{{label}}} "
                       f"{esc(' '.join(str(entry[key]).split()))}")
        out.append("\\par\\smallskip\\noindent\\textbf{Checked today by the test suite.}")
        out.append("\\begin{itemize}")
        items = entry["verified_now"]
        if isinstance(items, str):
            items = [items]
        for item in items:
            out.append(f"\\item {esc(' '.join(str(item).split()))}")
        out.append("\\end{itemize}")
        out.append(f"\\par\\noindent\\textbf{{What to look for in the GIF.}} "
                   f"{esc(' '.join(str(entry['gif']).split()))}")
        out.append("")
    return "\n".join(out)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail if the generated files differ from the ones in the tree",
    )
    args = parser.parse_args()

    cfg = dict(load_config())
    yaml_path = Path(resolve_path())
    units = harvest_units(yaml_path.read_text(encoding="utf-8"))
    values = flatten(cfg)

    contracts = read_contracts_yaml()
    bands = cpp_band_names()
    problems = cross_check_contracts(contracts, values, bands)
    if problems:
        for p in problems:
            print(f"gen_concepts_values: contracts mismatch: {p}", file=sys.stderr)
        return 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    outputs: dict[str, str] = {}

    def emit(name: str, text: str) -> None:
        outputs[name] = text

    emit("macros.tex", emit_macros(values))
    emit("code-macros.tex", emit_code_macros(build_code_values()))

    loader_grid_table = emit_loader_grid_table()

    for stage in STAGES:
        sections = STAGE_SECTIONS.get(stage)
        if sections is None:
            continue
        rows = []
        for key in sorted(values):
            root = key.split(".", 1)[0]
            if root not in sections:
                continue
            rows.append((key, format_value(values[key]), units.get(key, "")))
        params = emit_params_table(rows, f"{stage}: model parameters")
        if stage in ("download", "ingest"):
            params += loader_grid_table
        emit(f"params-{stage}.tex", params)

    emit("params-download.tex", emit_download_params() + loader_grid_table)
    emit("params-scoring.tex", emit_scoring_params())
    emit("params-training.tex", emit_training_params())
    emit("params-prediction.tex", emit_prediction_params())
    emit("contracts.tex", emit_contracts(contracts, cfg, values))
    emit("scenarios-abm.tex", emit_scenarios())

    if args.check:
        # Byte-identical to what the tree holds: the generated files are
        # the source of truth for the documents, so a drift between the
        # code and the committed fragments must fail here.
        drifted: list[str] = []
        for name in sorted(outputs):
            path = OUT_DIR / name
            if not path.exists():
                drifted.append(f"{name}: missing")
                continue
            if path.read_text(encoding="utf-8") != outputs[name]:
                drifted.append(f"{name}: differs from the generated text")
        if drifted:
            for line in drifted:
                print(f"gen_concepts_values: {line}", file=sys.stderr)
            return 1
        print(
            f"gen_concepts_values: {len(outputs)} generated files are "
            "byte-identical to the tree"
        )
        return 0

    for name, text in outputs.items():
        (OUT_DIR / name).write_text(text, encoding="utf-8")

    print(f"gen_concepts_values: wrote {len(outputs)} files to {OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
