"""
Convert raw documents (XML, PDF, HTML) in data/ to .txt and store in sec-edgar-filings/processed/.

This mimics the real pipeline: raw formats → processing → plain text for RAG.
Note: For SEC EDGAR, download_financial_docs.py gives full-submission.txt directly.
      This script is for when you have XML/PDF/HTML from other sources (e.g. manual download).

Run: python scripts/process_documents.py
"""
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
INPUT_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "sec-edgar-filings" / "processed"
MIN_TEXT_LENGTH = 1000  # Warn if extracted text is shorter (likely wrong file type)


def extract_from_xml(path: Path) -> str:
    """Extract text from XML. Strips tags, keeps content."""
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return path.read_text(encoding="utf-8", errors="ignore")

    raw = path.read_text(encoding="utf-8", errors="ignore")
    try:
        soup = BeautifulSoup(raw, "xml")
    except Exception:
        soup = BeautifulSoup(raw, "html.parser")  # Fallback for XML-like HTML
    for tag in soup(["script", "style"]):
        tag.decompose()
    text = soup.get_text(separator="\n", strip=True)
    return "\n".join(line for line in text.splitlines() if line)


def extract_from_html(path: Path) -> str:
    """Extract text from HTML."""
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return path.read_text(encoding="utf-8", errors="ignore")

    soup = BeautifulSoup(path.read_text(encoding="utf-8", errors="ignore"), "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    text = soup.get_text(separator="\n", strip=True)
    return "\n".join(line for line in text.splitlines() if line)


def extract_from_pdf(path: Path) -> str:
    """Extract text from PDF."""
    try:
        from pypdf import PdfReader
    except ImportError:
        raise ImportError("Install pypdf: pip install pypdf")

    reader = PdfReader(path)
    texts = []
    for page in reader.pages:
        texts.append(page.extract_text() or "")
    return "\n".join(texts)


def process_file(path: Path) -> str | None:
    """Convert a single file to plain text. Returns text or None if unsupported."""
    ext = path.suffix.lower()
    if ext in (".xml", ".xhtml"):
        return extract_from_xml(path)
    if ext in (".htm", ".html"):
        return extract_from_html(path)
    if ext == ".pdf":
        return extract_from_pdf(path)
    return None


def process_data_folder():
    """
    Process all XML, PDF, HTML files in data/ → convert to .txt → save to sec-edgar-filings/processed/.
    """
    if not INPUT_DIR.exists():
        print(f"Input folder not found: {INPUT_DIR}")
        return

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    extensions = {".xml", ".xhtml", ".htm", ".html", ".pdf"}
    files = [f for f in INPUT_DIR.iterdir() if f.is_file() and f.suffix.lower() in extensions]

    if not files:
        print(f"No XML, HTML, or PDF files found in {INPUT_DIR}")
        return

    for path in files:
        try:
            text = process_file(path)
            if text is None:
                print(f"  Skip (unsupported): {path.name}")
                continue

            out_name = path.stem + ".txt"
            out_path = OUTPUT_DIR / out_name

            if len(text) < MIN_TEXT_LENGTH:
                print(f"  Warning: {path.name} → only {len(text)} chars (may be wrong file type, e.g. viewer page)")

            out_path.write_text(text, encoding="utf-8")
            print(f"  {path.name} → {out_path} ({len(text):,} chars)")
        except Exception as e:
            print(f"  Error processing {path.name}: {e}")

    print(f"\nDone. Output in {OUTPUT_DIR}")


if __name__ == "__main__":
    print("Processing raw documents in data/ → sec-edgar-filings/processed/")
    print("(Supports: .xml, .html, .htm, .pdf)\n")
    process_data_folder()
    print("\nTip: For SEC EDGAR, download_financial_docs.py gives full-submission.txt directly.")
