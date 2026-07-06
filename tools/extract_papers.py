"""Extract text from all PDFs in papers/ and create .md equivalents."""
from pathlib import Path
import sys

try:
    import pdfplumber
except ImportError:
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "pdfplumber", "--break-system-packages"], check=True)
    import pdfplumber

papers_dir = Path(__file__).resolve().parent.parent / "papers"

pdfs = list(papers_dir.rglob("*.pdf"))
print(f"Found {len(pdfs)} PDF files")

for pdf_path in sorted(pdfs):
    md_path = pdf_path.with_suffix(".md")
    print(f"  Extracting: {pdf_path.relative_to(papers_dir.parent)}")

    try:
        with pdfplumber.open(pdf_path) as pdf:
            text_parts = []
            for i, page in enumerate(pdf.pages):
                text = page.extract_text()
                if text:
                    text_parts.append(f"--- Page {i+1} ---\n{text}")
                else:
                    text_parts.append(f"--- Page {i+1} ---\n[No extractable text on this page]")

            full_text = "\n\n".join(text_parts)

        with open(md_path, "w", encoding="utf-8") as f:
            f.write(f"# {pdf_path.stem}\n\n")
            f.write(f"**Source PDF:** `{pdf_path.name}`  \n")
            f.write(f"**Path:** `{pdf_path.relative_to(papers_dir.parent)}`  \n\n")
            f.write("---\n\n")
            f.write(full_text)

        print(f"    -> Created {md_path.name} ({len(full_text)} chars)")
    except Exception as e:
        print(f"    -> ERROR: {e}")

print("\nDone!")
