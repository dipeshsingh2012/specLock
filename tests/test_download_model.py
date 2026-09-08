"""
Unit tests for model download helper script (scripts/download_model.py).
"""

from unittest.mock import patch
from scripts.download_model import download_model


def test_download_model_invokes_sentence_transformer(monkeypatch):
    """Verify download_model triggers SentenceTransformer with expected cache_folder."""
    monkeypatch.setenv("HF_HOME", "/custom/model/cache")

    with patch("scripts.download_model.SentenceTransformer") as mock_st:
        download_model("sentence-transformers/all-MiniLM-L6-v2")
        mock_st.assert_called_once_with(
            "sentence-transformers/all-MiniLM-L6-v2",
            cache_folder="/custom/model/cache",
        )


def test_download_model_default_cache_dir(monkeypatch):
    """Verify default cache dir fallback is /app/model_cache when HF_HOME unset."""
    monkeypatch.delenv("HF_HOME", raising=False)

    with patch("scripts.download_model.SentenceTransformer") as mock_st:
        download_model()
        mock_st.assert_called_once_with(
            "sentence-transformers/all-MiniLM-L6-v2",
            cache_folder="/app/model_cache",
        )
