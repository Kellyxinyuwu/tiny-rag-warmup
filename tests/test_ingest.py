"""
Unit tests for tiny_rag.ingest.
"""
import pytest

from tiny_rag.ingest import chunk_with_overlap, load_txt


class TestChunkWithOverlap:
    def test_short_text_single_chunk(self):
        text = "Hello world. This is a short text."
        chunks = chunk_with_overlap(text, chunk_size=100, overlap=20)
        assert len(chunks) >= 1
        assert all(isinstance(c, str) for c in chunks)
        assert "Hello" in chunks[0]

    def test_long_text_multiple_chunks(self):
        text = "word " * 300
        chunks = chunk_with_overlap(text, chunk_size=50, overlap=10)
        assert len(chunks) >= 2

    def test_empty_text_returns_empty_list(self):
        chunks = chunk_with_overlap("", chunk_size=100, overlap=20)
        assert chunks == []

    def test_chunk_size_not_exceeded(self):
        text = "word " * 500
        chunks = chunk_with_overlap(text, chunk_size=50, overlap=10)
        encoding = __import__("tiktoken").get_encoding("cl100k_base")
        for c in chunks:
            tokens = encoding.encode(c)
            assert len(tokens) <= 55  # chunk_size + small variance


class TestLoadTxt:
    def test_loads_file(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("Hello world", encoding="utf-8")
        assert load_txt(f) == "Hello world"

    def test_ignores_encoding_errors(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_bytes(b"Valid \xff invalid")
        result = load_txt(f)
        assert "Valid" in result
