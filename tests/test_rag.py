"""
Unit tests for tiny_rag.rag.
"""
import pytest

from tiny_rag.rag import build_rag_prompt, infer_ticker_from_query


class TestInferTickerFromQuery:
    def test_alphabet_returns_googl(self):
        assert infer_ticker_from_query("What are Alphabet's main risks?") == "GOOGL"

    def test_google_returns_googl(self):
        assert infer_ticker_from_query("Tell me about Google") == "GOOGL"

    def test_apple_returns_aapl(self):
        assert infer_ticker_from_query("Apple's revenue") == "AAPL"

    def test_microsoft_returns_msft(self):
        assert infer_ticker_from_query("Microsoft cloud") == "MSFT"

    def test_unknown_returns_none(self):
        assert infer_ticker_from_query("What is the weather?") is None

    def test_case_insensitive(self):
        assert infer_ticker_from_query("ALPHABET risks") == "GOOGL"
        assert infer_ticker_from_query("APPLE stock") == "AAPL"


class TestBuildRagPrompt:
    def test_includes_context_and_question(self):
        contexts = [
            {"content": "Risk factors include cybersecurity.", "ticker": "GOOGL"},
            {"content": "Revenue grew 10%.", "ticker": "GOOGL"},
        ]
        prompt = build_rag_prompt("What are the risks?", contexts)
        assert "Risk factors include cybersecurity" in prompt
        assert "Revenue grew 10%" in prompt
        assert "What are the risks?" in prompt

    def test_citation_instructions(self):
        contexts = [{"content": "Test.", "ticker": "AAPL"}]
        prompt = build_rag_prompt("Q?", contexts)
        assert "Cite sources" in prompt or "[1]" in prompt

    def test_context_numbering(self):
        contexts = [
            {"content": "First.", "ticker": "A"},
            {"content": "Second.", "ticker": "B"},
        ]
        prompt = build_rag_prompt("Q?", contexts)
        assert "[1]" in prompt
        assert "[2]" in prompt
        assert "(A)" in prompt
        assert "(B)" in prompt
