"""
Integration tests for tiny_rag.api.
"""
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from tiny_rag.api import app

client = TestClient(app)


class TestRoot:
    def test_returns_200(self):
        r = client.get("/")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"
        assert "docs" in r.json()


class TestHealth:
    def test_health_returns_json(self):
        r = client.get("/health")
        assert r.status_code in (200, 503)
        data = r.json()
        assert "status" in data
        assert "database" in data
        assert "ollama" in data

    @patch("tiny_rag.api.check_database")
    @patch("tiny_rag.api.check_ollama")
    def test_health_200_when_all_ok(self, mock_ollama, mock_db):
        mock_db.return_value = (True, "ok")
        mock_ollama.return_value = (True, "ok")
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "healthy"

    @patch("tiny_rag.api.check_database")
    @patch("tiny_rag.api.check_ollama")
    def test_health_503_when_db_fails(self, mock_ollama, mock_db):
        mock_db.return_value = (False, "connection refused")
        mock_ollama.return_value = (True, "ok")
        r = client.get("/health")
        assert r.status_code == 503
        assert r.json()["status"] == "unhealthy"
        assert r.json()["database"] == "connection refused"


class TestAsk:
    @patch("tiny_rag.api.answer_with_rag")
    def test_ask_returns_answer_when_auth_disabled(self, mock_rag):
        mock_rag.return_value = {
            "answer": "Test answer.",
            "sources": [{"ticker": "GOOGL", "content": "..."}],
        }
        r = client.get("/ask", params={"q": "What are Alphabet's risks?"})
        assert r.status_code == 200
        data = r.json()
        assert data["answer"] == "Test answer."
        assert data["sources_count"] == 1
        mock_rag.assert_called_once()

    @patch("tiny_rag.api.answer_with_rag")
    def test_ask_respects_k_param(self, mock_rag):
        mock_rag.return_value = {"answer": "A", "sources": []}
        r = client.get("/ask", params={"q": "test", "k": 10})
        assert r.status_code == 200
        mock_rag.assert_called_once()
        call_kwargs = mock_rag.call_args[1]
        assert call_kwargs["k"] == 10

    def test_ask_requires_q(self):
        r = client.get("/ask")
        assert r.status_code == 422
