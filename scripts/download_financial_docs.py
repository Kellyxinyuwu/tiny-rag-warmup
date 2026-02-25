"""
Download financial documents from SEC EDGAR for the RAG project.
Requires: pip install sec-edgar-downloader

Run: python scripts/download_financial_docs.py
"""
from pathlib import Path

# Paths relative to project root (parent of scripts/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# SEC requires a company name and email for programmatic access
COMPANY_NAME = "University of Hong Kong"  # Change this
COMPANY_EMAIL = "kellywxy@connect.hku.hk"  # Change this
OUTPUT_DIR = PROJECT_ROOT / "data"

# Tickers to download (add more as needed)
TICKERS = ["AAPL", "GOOGL"]  # Apple, Alphabet (Google)


def download_10k_filings():
    """Download latest 10-K filings for each ticker."""
    from sec_edgar_downloader import Downloader

    OUTPUT_DIR.mkdir(exist_ok=True)
    dl = Downloader(COMPANY_NAME, COMPANY_EMAIL)

    for ticker in TICKERS:
        print(f"Downloading 10-K for {ticker}...")
        dl.get("10-K", ticker, limit=1)
        print(f"  Done. Check sec-edgar-filings/{ticker}/")

    print("\nFilings saved to sec-edgar-filings/")
    print("Run extract_text_from_filings() to convert to plain text for ingest.py")


def extract_text_from_filings():
    """
    Extract plain text from downloaded SEC filings (HTML format).
    Saves to data/{ticker}_10k.txt for use in ingest.py.
    """
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        print("Install beautifulsoup4: pip install beautifulsoup4")
        return

    filings_dir = PROJECT_ROOT / "sec-edgar-filings"
    if not filings_dir.exists():
        print("Download filings first: run download_10k_filings()")
        return

    OUTPUT_DIR.mkdir(exist_ok=True)

    for ticker_dir in filings_dir.iterdir():
        if not ticker_dir.is_dir():
            continue

        ten_k_dir = ticker_dir / "10-K"
        if not ten_k_dir.exists():
            continue

        # Find the most recent filing folder (SEC uses accession numbers like 0000320193-24-000105)
        filing_folders = sorted(
            [p for p in ten_k_dir.iterdir() if p.is_dir()],
            key=lambda p: p.name,
            reverse=True,
        )
        for folder in filing_folders:
            # Look for .htm or .html (skip index files)
            html_files = list(folder.glob("*.htm")) + list(folder.glob("*.html"))
            html_files = [f for f in html_files if "index" not in f.name.lower()]
            if not html_files:
                continue
            # Prefer "full" or largest file
            html_file = max(
                html_files,
                key=lambda f: ("full" in f.name.lower(), f.stat().st_size),
            )
            text = extract_text_from_html(html_file)
            if len(text) > 1000:
                out_path = OUTPUT_DIR / f"{ticker_dir.name}_10k.txt"
                out_path.write_text(text, encoding="utf-8")
                print(f"Saved: {out_path} ({len(text):,} chars)")
            break


def extract_text_from_html(html_path: Path) -> str:
    """Extract readable text from SEC HTML filing."""
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return html_path.read_text(encoding="utf-8", errors="ignore")  # Fallback: raw

    soup = BeautifulSoup(html_path.read_text(encoding="utf-8", errors="ignore"), "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    text = soup.get_text(separator="\n", strip=True)
    return "\n".join(line for line in text.splitlines() if line)


if __name__ == "__main__":
    print("Step 1: Download 10-K filings from SEC EDGAR")
    print("(Edit COMPANY_NAME and COMPANY_EMAIL at top of this file first!)\n")

    download_10k_filings()

    print("\nStep 2: Extract plain text for ingest.py")
    extract_text_from_filings()

    print("\nDone. Use data/*.txt files with ingest.py")
