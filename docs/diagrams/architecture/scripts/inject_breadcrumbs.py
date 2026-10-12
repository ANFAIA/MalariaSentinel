#!/usr/bin/env python3
"""Inject Breadcrumbs codeblocks + Dataview edge-detail block en cada nota del vault ABM.

Idempotente: los blockes viven entre marcadores
<!-- bc:auto:start v1 --> ... <!-- bc:auto:end -->
Si ya existen, se reemplazan en sitio. No toca nada más de la nota.

Bloques generados por nota:
1. breadcrumbs mermaid local (vecindario, aristas etiquetadas por tipo de edge)
2. Dataview table: detalle de cada edge con la llamada exacta (parsa tabla Conexiones)
"""
import re
import sys
from pathlib import Path
import yaml

BASE = Path("docs/diagrams/architecture")
START = "<!-- bc:auto:start -->"
END = "<!-- bc:auto:end -->"

# tipos de edge que Breadcrumbs conoce (edge fields registrados)
EDGE_TYPES = ["up", "calls", "called_by", "owns", "reads", "writes", "related"]


def load_note(path: Path):
    """Returns (fm_dict, fm_text_full, body)."""
    text = path.read_text(encoding="utf-8")
    m = re.match(r"\A(---\n.*?\n---\n)(.*)\Z", text, re.S)
    if not m:
        return None, "", text
    try:
        fm = yaml.safe_load(m.group(1)[4:-4] or "{}")
    except Exception as e:  # noqa: BLE001
        print(f"  !! yaml error {path.name}: {e}", file=sys.stderr)
        fm = {}
    return (fm if isinstance(fm, dict) else {}), m.group(1), m.group(2)


def process(path: Path) -> bool:
    fm, fm_text, body = load_note(path)
    if fm is None:
        print(f"  sin frontmatter, skip: {path.name}")
        return False


def extract_conexiones_rows(body: str):
    """Parsa la tabla '## Conexiones' → filas [desde, llama_a, en, detalle]."""
    rows = []
    m = re.search(r"## Conexiones[^\n]*\n(.*?)(?=\n## |\nup::|\Z)", body, re.S)
    if not m:
        return rows
    for line in m.group(1).splitlines():
        line = line.strip()
        if not line.startswith("|") or line.startswith("| Desde") or line.startswith("|---"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) >= 4:
            rows.append(cells)
    return rows


def build_bc_block(fm: dict) -> str:
    """Codeblock breadcrumbs mermaid local (vecindario, aristas etiquetadas por field).

    Sintaxis 4.22.x validada contra docs 2026-10:
    - depth SIEMPRE lista: depth: [0, 1]
    - show-attributes: lista de atributos de edge, p.ej. [field]
    - fields se omite → usa TODOS los edge fields registrados (calls, owns, ...).
      El validator del plugin solo acepta sus 5 fields genéricos en `fields:`,
      por eso no lo tocamos.
    - sort: field agrupa el árbol/lista por tipo de edge (= Matrix View).
    """
    has_edges = any(fm.get(f) for f in EDGE_TYPES)
    if not has_edges:
        return ""
    return (
        "```breadcrumbs\n"
        "type: mermaid\n"
        "depth: [0, 1]\n"
        "sort: field\n"
        "show-attributes: [field]\n"
        "mermaid-direction: LR\n"
        "mermaid-arrow: true\n"
        "```\n"
    )


def build_dv_block(nodename: str, rows) -> str:
    """Detalle por edge: fuente = tabla Conexiones de la propia nota."""
    if not rows:
        return ""
    lines = ["| método llamador | llamada → destino | en archivo | detalle / firma |", "|---|---|---|---|"]
    for r in rows:
        cells = [c.replace("|", "\\|") for c in r[:4]] + [""] * (4 - len(r[:4]))
        lines.append("| " + " | ".join(cells) + " |")
    table = "\n".join(lines)
    return f"> [!info] Conexiones exactas del grafo\n> **Nodo actual · nota: {nodename}**\n> *Mantenida manualmente — fuente: cpp real + índice codebase (“no es suposición”).*\n{table}\n"


EDGE_FIELDS = ["up", "related", "calls", "called_by", "owns", "reads", "writes"]


def process(path: Path) -> bool:
    fm, fm_text, body = load_note(path)
    if fm is None:
        print(f"  sin frontmatter, skip: {path.name}")
        return False
    # nota ya procesada: quitar bloque previo para regenerar
    body = re.sub(re.escape(START) + r".*?" + re.escape(END) + r"\n?", "", body, flags=re.S)
    bc = build_bc_block(fm)
    rows = extract_conexiones_rows(body)
    dv = build_dv_block(path.stem.replace("-", " "), rows)
    if not bc and not dv:
        return False
    block = f"{START}\n{bc}\n{dv}\n{END}\n"
    # insertar tras la línea up:: (o al final si no existe)
    lines = body.splitlines(keepends=True)
    out = []
    inserted = False
    for ln in lines:
        if not inserted and ln.startswith("up::"):
            out.append(ln)
            out.append("\n" + block)
            inserted = True
        else:
            out.append(ln)
    if not inserted:
        out.append("\n" + block)
    new_body = "".join(out)
    path.write_text(fm_text + new_body, encoding="utf-8")
    return True


def main():
    files = sorted(BASE.rglob("*.md"))
    n = 0
    for f in files:
        if process(f):
            n += 1
            print("  ok:", f.name)
    print(f"procesadas: {n}/{len(files)}")


if __name__ == "__main__":
    main()
