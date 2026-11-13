---
name: pdf
description: Use this skill only to create or modify PDF files, including merging, splitting, rotating, watermarking, filling forms, encrypting, or otherwise editing PDFs. Do not use it to read, summarize, OCR, extract, or interpret PDF content; use the docling skill for extraction and analysis.
license: Proprietary. LICENSE.txt has complete terms
---

# PDF Editing Guide

## Scope and routing

Use this skill when the requested deliverable is a newly created or modified PDF file. Examples include creating a PDF, merging or splitting files, rotating pages, adding/removing pages or watermarks, filling forms, or applying password protection.

Do not use this skill to read, summarize, translate, OCR, extract text/tables/images, or interpret the contents of a PDF. Use the `docling` skill for all content extraction, including basic text extraction. If a request requires both understanding content and changing a PDF, use Docling for extraction first, then this skill for the edit.

## Python execution

Run Python code for PDF editing through `uvx`; do not use bare `python`, `python3`, `pip`, or `pip install`, and do not create or activate a virtual environment. Use `uvx --with <package> ... python <script.py> [args]`, adding each required PyPI dependency with its own `--with` option. Native executables such as `qpdf` and `pdftk` are not Python packages and can be run directly if installed.

Example:

```bash
uvx --with pypdf python merge.py input1.pdf input2.pdf output.pdf
```

## Common editing operations

### Merge PDFs

```python
from pypdf import PdfReader, PdfWriter

writer = PdfWriter()
for path in ["doc1.pdf", "doc2.pdf"]:
    for page in PdfReader(path).pages:
        writer.add_page(page)
with open("merged.pdf", "wb") as output:
    writer.write(output)
```

### Split a PDF into one file per page

```python
from pypdf import PdfReader, PdfWriter

for index, page in enumerate(PdfReader("input.pdf").pages, start=1):
    writer = PdfWriter()
    writer.add_page(page)
    with open(f"page_{index}.pdf", "wb") as output:
        writer.write(output)
```

### Rotate pages

```python
from pypdf import PdfReader, PdfWriter

reader = PdfReader("input.pdf")
writer = PdfWriter()
for page in reader.pages:
    writer.add_page(page)
writer.pages[0].rotate(90)
with open("rotated.pdf", "wb") as output:
    writer.write(output)
```

### Add a watermark

```python
from pypdf import PdfReader, PdfWriter

watermark = PdfReader("watermark.pdf").pages[0]
reader = PdfReader("input.pdf")
writer = PdfWriter()
for page in reader.pages:
    page.merge_page(watermark)
    writer.add_page(page)
with open("watermarked.pdf", "wb") as output:
    writer.write(output)
```

### Create a PDF

Use ReportLab for programmatic PDF creation. Use Paragraph markup such as `<sub>` and `<super>` for subscripts/superscripts; do not use Unicode subscript/superscript glyphs with built-in fonts because they may render as missing-glyph boxes.

## Forms

For creating, inspecting, or filling PDF forms, read `forms.md` and follow its instructions. Preserve the original file unless the user asks to overwrite it; write the result to a separate path by default.

## Command-line alternatives

Use `qpdf` or `pdftk` when installed and appropriate for merge, split, rotate, or encryption tasks. Check the executable's local help if syntax or support is uncertain. Do not use extraction commands such as `pdftotext` or OCR/image extraction as a substitute for the `docling` skill.

## Verification

After editing, confirm the output file exists and is a valid PDF. For transformations, check page count and requested page order/orientation where practical. For forms, verify the requested fields and values without unintentionally changing unrelated fields. Report any operation that could not be verified.

## Reference material

`reference.md` contains additional library examples, including some extraction material. For any task whose goal is to read or extract document content, ignore those extraction sections and route to the `docling` skill; this skill's scope remains PDF creation and modification.
