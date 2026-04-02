"""Unit tests for AI Service — no network, no LLM calls."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from fastapi.testclient import TestClient
from main import app, _documents, _chunk_text, _simple_similarity

client = TestClient(app)

@pytest.fixture(autouse=True)
def clear_documents():
    _documents.clear()
    yield
    _documents.clear()

class TestChunkText:
    def test_splits_long_text_into_chunks(self):
        text   = " ".join([f"word{i}" for i in range(1000)])
        chunks = _chunk_text(text, size=100, overlap=10)
        assert len(chunks) > 1

    def test_short_text_returns_single_chunk(self):
        chunks = _chunk_text("Hello world", size=100)
        assert len(chunks) == 1

class TestSimilarity:
    def test_exact_match_returns_one(self):
        assert _simple_similarity("hello world", "hello world") == 1.0

    def test_no_match_returns_zero(self):
        assert _simple_similarity("hello", "goodbye") == 0.0

    def test_partial_match_between_zero_and_one(self):
        score = _simple_similarity("hello world", "hello there")
        assert 0.0 < score < 1.0

class TestUploadEndpoint:
    def test_upload_valid_document(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("This is a test document about microservices and Docker.")
        with open(f, "rb") as fp:
            response = client.post("/documents/upload", files={"file": ("test.txt", fp, "text/plain")})
        assert response.status_code == 200
        data = response.json()
        assert "doc_id" in data
        assert data["chunks_indexed"] >= 1

    def test_upload_empty_file(self, tmp_path):
        f = tmp_path / "empty.txt"
        f.write_text("")
        with open(f, "rb") as fp:
            response = client.post("/documents/upload", files={"file": ("empty.txt", fp, "text/plain")})
        assert response.status_code == 400

class TestAskEndpoint:
    def _upload_doc(self, tmp_path, content="Microservices use RabbitMQ for messaging."):
        f = tmp_path / "doc.txt"
        f.write_text(content)
        with open(f, "rb") as fp:
            r = client.post("/documents/upload", files={"file": ("doc.txt", fp, "text/plain")})
        return r.json()["doc_id"]

    def test_ask_returns_answer(self, tmp_path):
        doc_id   = self._upload_doc(tmp_path)
        response = client.post("/documents/ask", json={"doc_id": doc_id, "question": "What is RabbitMQ used for?"})
        assert response.status_code == 200
        assert "answer" in response.json()

    def test_ask_nonexistent_doc_returns_404(self):
        response = client.post("/documents/ask", json={"doc_id": "nonexistent", "question": "test"})
        assert response.status_code == 404
