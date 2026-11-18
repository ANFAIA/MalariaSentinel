"""Extract a paper's PDF to Markdown with the ``docling`` console script.

The command is an argument list, never a shell string. The flags are fixed:
``--tables`` and ``--ocr`` on, picture description off, images exported as
referenced files. The device is ``cpu`` by default and ``mps`` is opt-in. The
docling version and the device go to ``provenance.yaml``.

The project's ``docling-mps`` wrapper is not used (plan §6.5); the portable
``docling`` script is.

Docling Markdown is a local working file, not a citation target and not a source
of truth (D22). A failed extraction is recorded as ``pending_extraction_failed``
and never raises.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import DEVICES
from .manifest import Entry
from .provenance import update_provenance, utc_now_iso

EXTRACT_FLAGS = (
    "--to",
    "md",
    "--tables",
    "--ocr",
    "--no-enrich-picture-description",
    "--image-export-mode",
    "referenced",
)
IMAGES_DIR = "images"
Runner = Callable[..., Any]


@dataclass(frozen=True)
class ExtractResult:
    """Outcome of extracting one paper's PDF to Markdown with docling."""
    paper_id: str
    status: str  # extracted | failed | skipped
    markdown_path: Path | None
    observed_status: str | None
    detail: str = ""


def validate_device(device: str) -> str:
    """Return the device if it is one of DEVICES; raise ValueError otherwise."""
    if device not in DEVICES:
        raise ValueError(f"device must be one of {DEVICES}, got {device!r}")
    return device


def docling_command(pdf: Path, out_dir: Path, *, device: str, docling_bin: str = "docling") -> list[str]:
    """The exact argument list passed to ``subprocess.run`` (no shell)."""
    validate_device(device)
    return [docling_bin, "convert", *EXTRACT_FLAGS, "--device", device, "--output", str(out_dir), str(pdf)]


def docling_version(docling_bin: str = "docling", run: Runner = subprocess.run) -> str:
    """Version reported by ``docling --version``, or ``unknown``."""
    try:
        proc = run([docling_bin, "--version"], capture_output=True, text=True, check=False)
    except OSError:
        return "unknown"
    match = re.search(r"Docling version:\s*(\S+)", proc.stdout or "")
    return match.group(1) if match else "unknown"


def _rename_artifacts(paper_dir: Path, slug: str, markdown: Path) -> str:
    """Move docling's ``<slug>_artifacts/`` to ``images/`` and rewrite the links."""
    src = paper_dir / f"{slug}_artifacts"
    if not src.is_dir():
        return "no image artifacts"
    dst = paper_dir / IMAGES_DIR
    if dst.exists():
        return f"{IMAGES_DIR}/ already exists; left {src.name}/ in place"
    src.rename(dst)
    text = markdown.read_text(encoding="utf-8")
    markdown.write_text(text.replace(f"{src.name}/", f"{IMAGES_DIR}/"), encoding="utf-8")
    return f"artifacts moved to {IMAGES_DIR}/"


def extract_entry(
    entry: Entry,
    papers_root: Path,
    *,
    device: str,
    docling_bin: str = "docling",
    run: Runner = subprocess.run,
    version: str | None = None,
    extracted_at: str | None = None,
) -> ExtractResult:
    """Run docling on one paper's PDF and record the outcome in its provenance."""
    validate_device(device)
    paper_dir = papers_root / entry.theme / entry.slug
    pdf = paper_dir / f"{entry.slug}.pdf"
    if not pdf.is_file():
        return ExtractResult(entry.id, "skipped", None, None, "no PDF in the paper folder; run fetch first")

    stamp = extracted_at or utc_now_iso()
    ver = version or docling_version(docling_bin, run)
    command = docling_command(pdf, paper_dir, device=device, docling_bin=docling_bin)
    base: dict[str, Any] = {
        "tool": "docling",
        "docling_version": ver,
        "device": device,
        "flags": list(EXTRACT_FLAGS),
        "extracted_at": stamp,
    }

    def failed(detail: str, returncode: int | None) -> ExtractResult:
        """Record a failed extraction in provenance and return the matching result."""
        update_provenance(
            paper_dir,
            observed_status="pending_extraction_failed",
            extract={**base, "status": "failed", "returncode": returncode, "detail": detail},
        )
        return ExtractResult(entry.id, "failed", None, "pending_extraction_failed", detail)

    try:
        proc = run(command, capture_output=True, text=True, check=False)
    except OSError as exc:
        return failed(f"cannot run docling: {exc}", None)
    if proc.returncode != 0:
        tail = (proc.stderr or "").strip().splitlines()[-3:]
        return failed(" | ".join(tail) or f"docling exited with {proc.returncode}", proc.returncode)

    markdown = paper_dir / f"{entry.slug}.md"
    if not markdown.is_file():
        return failed(f"docling produced no {markdown.name}", proc.returncode)

    artifacts = _rename_artifacts(paper_dir, entry.slug, markdown)
    update_provenance(
        paper_dir,
        observed_status="ok",
        extract={**base, "status": "extracted", "returncode": proc.returncode, "detail": artifacts},
    )
    return ExtractResult(entry.id, "extracted", markdown, "ok", artifacts)
