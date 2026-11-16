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
import re
import sys
from collections.abc import Mapping
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
        if sentinel is not None:
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
    import ast

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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail if the generated files differ from the committed ones",
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
    written: list[Path] = []

    def write(name: str, text: str) -> None:
        path = OUT_DIR / name
        path.write_text(text, encoding="utf-8")
        written.append(path)

    write("macros.tex", emit_macros(values))

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
        write(f"params-{stage}.tex", emit_params_table(rows, f"{stage}: model parameters"))

    write("params-download.tex", emit_download_params())
    write("params-scoring.tex", emit_scoring_params())
    write("params-training.tex", emit_training_params())
    write("params-prediction.tex", emit_prediction_params())
    write("contracts.tex", emit_contracts(contracts, cfg, values))

    if args.check:
        import subprocess

        diff = subprocess.run(
            ["git", "diff", "--exit-code", "--", str(OUT_DIR.relative_to(REPO))],
            cwd=REPO,
            capture_output=True,
            text=True,
        )
        if diff.returncode != 0:
            sys.stderr.write(diff.stdout)
            print("gen_concepts_values: generated files differ from the tree", file=sys.stderr)
            return 1

    print(f"gen_concepts_values: wrote {len(written)} files to {OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
