"""
Evaluate RAG on a set of Q&A pairs.

GUIDE:
------
1. load_qa_pairs() → Load from eval_qa.json (q, ticker, expected_keywords)
2. run_eval()      → For each question: answer_with_rag() → check keywords → record
3. print_report()  → Summary: passed/failed, per-question details
4. save_to_excel() → Write eval_results.xlsx (question, answer, ticker, sources_count, time_sec, passed, keywords_found, keywords_missed)

expected_keywords: You define in JSON. Eval checks if answer contains them.
  PASS = all found; FAIL = any missed; N/A = no keywords defined

Run: python -m tiny_rag.eval
Runtime: ~10–15 min for 50 questions (each ~10–20 seconds)
"""
from dotenv import load_dotenv

load_dotenv()

import json
import time
from pathlib import Path

import pandas as pd

from .rag import answer_with_rag, infer_ticker_from_query


def load_qa_pairs(path: str = "eval_qa.json") -> list[dict]:
    """Load Q&A pairs from JSON file."""
    with open(path) as f:
        return json.load(f)


def run_eval(qa_pairs: list[dict], k: int = 6) -> list[dict]:
    """Run RAG on each question and collect results."""
    results = []
    total = len(qa_pairs)
    for i, item in enumerate(qa_pairs):
        q = item["q"]
        ticker = item.get("ticker") or infer_ticker_from_query(q)
        print(f"  [{i + 1}/{total}] {q[:60]}{'...' if len(q) > 60 else ''}")
        start = time.perf_counter()
        result = answer_with_rag(q, k=k, ticker=ticker)
        elapsed = time.perf_counter() - start
        print(f"       -> done in {elapsed:.1f}s")

        # Check expected keywords if provided
        expected = item.get("expected_keywords", [])
        answer_lower = result["answer"].lower()
        keywords_found = [kw for kw in expected if kw.lower() in answer_lower]
        keywords_missed = [kw for kw in expected if kw.lower() not in answer_lower]
        passed = len(keywords_missed) == 0 if expected else None

        results.append({
            "question": q,
            "answer": result["answer"],
            "sources_count": len(result["sources"]),
            "ticker": ticker,
            "time_sec": round(elapsed, 2),
            "keywords_found": ", ".join(keywords_found),
            "keywords_missed": ", ".join(keywords_missed),
            "passed": "PASS" if passed else ("FAIL" if passed is False else "N/A"),
        })
    return results


def print_report(results: list[dict]) -> None:
    """Print evaluation report."""
    total = len(results)
    passed = sum(1 for r in results if r["passed"] == "PASS")
    failed = sum(1 for r in results if r["passed"] == "FAIL")
    no_check = sum(1 for r in results if r["passed"] == "N/A")

    print("=" * 60)
    print("RAG EVALUATION REPORT")
    print("=" * 60)
    print(f"Total questions: {total}")
    if no_check < total:
        print(f"Passed (keywords): {passed}")
        print(f"Failed (keywords): {failed}")
    print(f"No keyword check: {no_check}")
    print()

    for i, r in enumerate(results, 1):
        print(f"[{i}] Q: {r['question']}")
        print(f"    Ticker: {r['ticker']} | Sources: {r['sources_count']} | Time: {r['time_sec']}s")
        if r["passed"] != "N/A":
            print(f"    Keywords: {r['passed']} (found: {r['keywords_found']}, missed: {r['keywords_missed']})")
        print(f"    Answer preview: {r['answer'][:150]}...")
        print()


def save_to_excel(results: list[dict], path: str | Path = "eval_results.xlsx") -> None:
    """Save results to Excel with question and answer columns."""
    df = pd.DataFrame(results)
    df.to_excel(path, index=False, engine="openpyxl")
    print(f"Results saved to {path}")


def main():
    project_root = Path(__file__).resolve().parent.parent.parent
    qa_path = project_root / "eval_qa.json"
    if not qa_path.exists():
        print(f"Error: {qa_path} not found")
        return

    qa = load_qa_pairs(str(qa_path))
    print(f"Running eval on {len(qa)} questions...\n")
    results = run_eval(qa)
    print_report(results)
    save_to_excel(results, project_root / "eval_results.xlsx")


if __name__ == "__main__":
    main()
