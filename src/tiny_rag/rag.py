"""
RAG answer: retrieve context, build prompt, call Ollama, return answer with citations.

GUIDE:
------
1. infer_ticker_from_query(query) → Maps "Alphabet" → GOOGL, "Apple" → AAPL (TICKER_MAP)
2. retrieve_context(query, k, ticker) → Get top-k chunks from retrieve.py
3. build_rag_prompt(query, contexts) → Format context + question + citation instructions
4. call_ollama(prompt) → Send to Ollama llama3.2, get response
5. answer_with_rag() → Orchestrates all above, returns {answer, sources}

Run: python -m tiny_rag.rag "What are Alphabet's main risks?"
Requires: Ollama running with llama3.2, ingested data
"""
from dotenv import load_dotenv

load_dotenv()

from .retrieve import retrieve_context


def build_rag_prompt(query: str, contexts: list[dict]) -> str:
    """Build prompt with retrieved context and citation instructions."""
    context_parts = []
    for i, ctx in enumerate(contexts, 1):
        content = ctx["content"].strip()
        ticker = ctx.get("ticker", "?")
        context_parts.append(f"[{i}] ({ticker})\n{content}")

    context_block = "\n\n---\n\n".join(context_parts)

    return f"""Use the following context to answer the question. Cite sources with [1], [2], etc.

Context:
{context_block}

Question: {query}

Answer (with citations):"""


def call_ollama(prompt: str, model: str = "llama3.2") -> str:
    """Call Ollama LLM and return the response text."""
    import ollama

    response = ollama.chat(model=model, messages=[{"role": "user", "content": prompt}])
    return response["message"]["content"]



def answer_with_rag(query: str, k: int = 5, ticker: str | None = None) -> dict:
    """
    Retrieve context, call LLM, return answer with citations.
    Returns: {"answer": str, "sources": list[dict]}
    """
    contexts = retrieve_context(query, k=k, ticker=ticker)
    if not contexts:
        return {"answer": "No relevant context found.", "sources": []}

    prompt = build_rag_prompt(query, contexts)
    answer = call_ollama(prompt)

    return {
        "answer": answer,
        "sources": [{"ticker": c["ticker"], "content": c["content"][:200] + "..."} for c in contexts],
    }


# Map company names (lowercase) to ticker symbols for focused retrieval.
# Used by infer_ticker_from_query() so "Alphabet's risks" → ticker=GOOGL
TICKER_MAP = {
    "alphabet": "GOOGL",
    "google": "GOOGL",
    "apple": "AAPL",
    "microsoft": "MSFT",
    "amazon": "AMZN",
    "meta": "META",
    "tesla": "TSLA",
    "nvidia": "NVDA",
}


def infer_ticker_from_query(query: str) -> str | None:
    """Infer ticker from query text if a known company is mentioned."""
    q = query.lower()
    for name, ticker in TICKER_MAP.items():
        if name in q:
            return ticker
    return None


if __name__ == "__main__":
    import sys

    query = sys.argv[1] if len(sys.argv) > 1 else "What are Apple's main risk factors?"
    ticker = infer_ticker_from_query(query)
    result = answer_with_rag(query, k=6, ticker=ticker)
    print("Answer:\n", result["answer"])
    print("\nSources:", len(result["sources"]))
