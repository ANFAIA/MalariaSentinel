---
name: docling
description: Use Docling whenever a PDF or image needs to be read, converted, searched, summarized, OCRed, or analyzed for text, structure, tables, figures, or diagrams. Use Docling for basic PDF text extraction too. Choose the lightest processing configuration that satisfies the task; use the installed docling-mps wrapper on this Apple Silicon Mac when its standard MPS pipeline is sufficient.
---

# Docling Document Extraction and Analysis

Use this skill to extract and understand document content. It covers PDFs and image files, including ordinary text extraction, OCR, layout and table recognition, and visual-content analysis. It does not replace the `pdf` skill for creating or modifying PDF files.

## Core rule: choose the level based on the task

The model chooses the processing level from the request and document characteristics; the user does not need to name a mode. Begin with the least costly level likely to work, then escalate only when a concrete need or observed extraction problem justifies it. Tell the user when a requested visual feature cannot be extracted by the selected pipeline.

| Level | Use when | Recommended approach |
|---|---|---|
| **Basic text and structure** | User wants to read, search, summarize, or translate an ordinary PDF; no special visual analysis requested | Run Docling's standard PDF pipeline and export Markdown. Use `docling-mps` on this Mac for its configured standard MPS conversion. |
| **Structured/OCR** | Scanned pages, mixed scanned/digital content, tables, multi-column layout, or text order matters | Use the standard pipeline with OCR and table structure enabled; the local wrapper already enables both. Inspect page/column order and tables that affect the answer. |
| **Visual content** | Meaning depends on figures, diagrams, charts, photos, or page appearance | Export images as referenced files and enable picture description as supported. Inspect the referenced image files as needed. For charts, use chart enrichment only if the chosen model/pipeline/device supports it; the local wrapper does not enable chart extraction. Do not claim a diagram was analyzed just because its image was exported or captioned. |
| **Image input** | User provides a standalone image or asks to read/analyze a page image | Try Docling's image conversion with the standard or appropriate VLM pipeline; select OCR/visual enrichment only as needed. Verify actual format support with `docling convert --help` or an attempted conversion. Do not assume the PDF-only wrapper accepts image inputs. |

If a PDF is digital and the task is simple text extraction, still use Docling. Do not default to pypdf/pdfplumber or a direct OCR tool for reading; reserve non-Docling utilities for cases Docling cannot handle or for PDF editing tasks routed to the `pdf` skill.

## Local setup and known wrapper

This Mac has Apple Silicon and the executable `docling-mps` available in PATH. It is a wrapper at `~/.local/bin/docling-mps` around the installed Docling CLI. The verified wrapper command is:

```bash
docling-mps input.pdf [output_dir]
```

If no output directory is supplied, it uses `./docling_out`. Its current configuration is:

```bash
docling convert "$1" \
  --pipeline standard \
  --device mps \
  --tables --ocr \
  --enrich-picture-description \
  --image-export-mode referenced \
  --to md \
  --output "${2:-./docling_out}"
```

This is a good default for common PDF extraction, especially when OCR, tables, and image descriptions are useful. It exports Markdown and referenced image assets. It is still a fixed wrapper: it does not expose arbitrary Docling options, and it does not enable chart-data extraction. Use the underlying `docling convert` CLI for options the wrapper does not expose, after checking compatibility and choosing an appropriate pipeline/device.

Installed versions observed on this machine: Docling 2.132.0, Docling Core 2.99.0, IBM Models 4.0.3, Docling Parse 7.22.1. These can change; query the installed CLI rather than treating this note as a permanent version guarantee.

## CLI workflow

### 1. Inspect the local CLI when needed

```bash
docling --version
docling convert --help
```

Use the help output as the authority for accepted input/output formats and available options on the installed version. Do not invent flags. `docling convert` accepts a local file, directory, or URL as source and defaults to Markdown output and the standard pipeline. Common relevant options include:

- `--to md|json|yaml|html|text|...`: choose output format. Markdown is the default and usually best for reading and summaries; JSON/YAML are useful when structured data is needed.
- `--pipeline standard|vlm|...`: select processing pipeline. Standard is the general-purpose choice. Use a VLM pipeline only when the task requires visual interpretation or standard extraction is insufficient, and verify model/device compatibility.
- `--device auto|cpu|mps|...`: choose accelerator. `mps` is available on this Apple Silicon setup, but not every model/preset supports it.
- `--ocr` / `--no-ocr`: OCR image-based content; OCR is enabled by default in the inspected installation.
- `--tables` / `--no-tables`: enable/disable table structure extraction; enabled by default in the inspected installation.
- `--ocr-engine`, `--ocr-lang`: configure OCR engine/language where necessary. Consult CLI help for accepted engine-specific language names.
- `--page-range 1-4`: limit conversion to a range of pages when supported by the selected backend.
- `--image-export-mode referenced|embedded|placeholder`: for image-capable outputs, reference separate exported PNG assets, embed assets, or mark image locations only. `text` output does not export images.
- `--enrich-picture-description`: add picture descriptions, if supported by selected pipeline/model/device.
- `--enrich-chart-*`: chart-data extraction option exists in the inspected CLI, but do not assume it is compatible with MPS or the wrapper's model preset. Verify before using.
- `--output DIR` or `--output-file FILE`: choose output location. `--output-file` requires one source and one output format.

### 2. Choose the least intensive suitable invocation

Basic PDF extraction on this Mac:

```bash
docling-mps "/path/to/input.pdf" "/path/to/output_dir"
```

This wrapper includes OCR, table extraction, picture descriptions, and referenced image export; for a simple text-only task that may be more processing than strictly necessary, but it is the known local, ready-to-use route. If minimizing enrichment/runtime is important, use the standard CLI with only the required options, after checking defaults and model compatibility:

```bash
docling convert "/path/to/input.pdf" --pipeline standard --to md --output "/path/to/output_dir"
```

For a scanned PDF or a document whose tables matter, explicitly retain OCR and tables (these are defaults in the inspected CLI, but explicit flags make intent clear):

```bash
docling convert "/path/to/input.pdf" --pipeline standard --ocr --tables --to md --output "/path/to/output_dir"
```

For visual assets and picture descriptions, use the installed wrapper or an equivalent CLI invocation with referenced image export and picture-description enrichment, provided the selected pipeline/device supports it. Example for testing the direct CLI:

```bash
docling convert "/path/to/input.pdf" \
  --pipeline standard --device mps --ocr --tables \
  --enrich-picture-description --image-export-mode referenced \
  --to md --output "/path/to/output_dir"
```

Do not add chart extraction or switch to a VLM preset blindly. The wrapper's known MPS configuration explicitly omits chart extraction because its chart preset was incompatible with MPS. Try a compatible alternative only after checking current CLI help and model/device constraints; report if chart extraction was unavailable.

For standalone images, use the CLI rather than `docling-mps` unless the wrapper has been verified to accept that specific image input:

```bash
docling convert "/path/to/image.png" --pipeline standard --to md --output "/path/to/output_dir"
```

If ordinary layout/OCR output does not satisfy a visual-analysis request, inspect `docling convert --help` for installed VLM options and available presets, then select a compatible combination. Do not assume all presets are local, run on MPS, or have the same capabilities. If conversion fails or the needed visual semantics are absent, state the limitation and use an appropriate available image-inspection capability rather than fabricating extracted content.

### 3. Inspect and use the output

- Locate the generated Markdown and any accompanying assets in the requested output directory.
- For `referenced` image export, open/inspect referenced image files when the answer depends on their content; a Markdown link or generated picture description alone is not proof that the visual was understood.
- Keep page numbers/section context when citing extracted facts, especially for tables, OCR, and diagrams. If the export does not provide reliable page attribution, say so rather than inventing it.
- For large documents, use page ranges or staged conversions where useful; preserve enough context to avoid missing cross-page tables or references.

## Standalone image processing

1. Identify the file and requested operation (read text, OCR, describe a figure, interpret a chart/diagram, or compare visual details).
2. Use Docling's direct image conversion if the installed CLI accepts the format. Select the standard pipeline for layout/OCR and consider a VLM pipeline only when image interpretation is required and the model/device are compatible.
3. If the CLI cannot accept the input format or output is inadequate, do not silently substitute an unrelated workflow. Explain the limitation and use an available image tool or convert the image to a supported format if that preserves the information.
4. Distinguish OCR transcription from visual interpretation. OCR can capture labels but does not necessarily explain relationships, axes, arrows, or diagram structure.

## Quality checks and reporting

Before using extracted content in an answer:

- Confirm conversion completed and output files exist; inspect errors/warnings.
- Check whether the document is digital, scanned, or mixed when that affects extraction quality.
- Ensure extracted text is non-empty and plausibly complete for the requested pages.
- Verify relevant table headers, row/column alignment, units, and numeric values against the source when consequential.
- Inspect suspicious reading order, multi-column merges, OCR substitutions, missing glyphs, and page breaks.
- If images are referenced, confirm the asset exists and inspect it when visual content matters.
- Treat descriptions, OCR, and chart extraction as model-derived results that may be wrong; label uncertainty and do not fill gaps by guessing.
- Report the chosen level when useful, plus any concrete limitation (for example: text/OCR extracted, but chart data not parsed).

## Scope boundary: PDF editing

For tasks whose deliverable is a modified or newly created PDF—merge, split, rotate, watermark, fill a form, encrypt, or create—load the `pdf` skill. When the user asks both to extract information and edit the PDF, use Docling for the extraction portion and the `pdf` skill for the modification portion.
