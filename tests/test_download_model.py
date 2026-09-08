"""
Unit tests for model download helper script (scripts/download_model.py).
"""

from unittest.mock import MagicMock, patch
from scripts.download_model import download_model


def test_download_model_invokes_sentence_transformer_and_save(monkeypatch, tmp_path):
    """Verify download_model fetches model and calls model.save to target directory."""
    custom_dir = str(tmp_path / "custom_model")
    monkeypatch.setenv("SPECLOCK_MODEL_DIR", custom_dir)

    mock_model = MagicMock()
    with patch("scripts.download_model.SentenceTransformer", return_value=mock_model) as mock_st:
        result = download_model("sentence-transformers/all-MiniLM-L6-v2")
        mock_st.assert_called_once_with("sentence-transformers/all-MiniLM-L6-v2")
        mock_model.save.assert_called_once_with(custom_dir)
        assert result == custom_dir


def test_download_model_default_target_dir(monkeypatch):
    """Verify default target dir fallback is /app/models/all-MiniLM-L6-v2 when unset."""
    monkeypatch.delenv("SPECLOCK_MODEL_DIR", raising=False)

    mock_model = MagicMock()
    with patch("scripts.download_model.SentenceTransformer", return_value=mock_model) as mock_st, \
         patch("scripts.download_model.os.makedirs") as mock_makedirs:
        result = download_model()
        mock_st.assert_called_once_with("sentence-transformers/all-MiniLM-L6-v2")
        mock_makedirs.assert_called_once_with("/app/models/all-MiniLM-L6-v2", exist_ok=True)
        mock_model.save.assert_called_once_with("/app/models/all-MiniLM-L6-v2")
        assert result == "/app/models/all-MiniLM-L6-v2"


def test_download_model_explicit_target_argument(tmp_path):
    """Verify explicit target_dir parameter overrides environment variable."""
    explicit_path = str(tmp_path / "explicit" / "model")
    mock_model = MagicMock()
    with patch("scripts.download_model.SentenceTransformer", return_value=mock_model) as mock_st:
        result = download_model("sentence-transformers/all-MiniLM-L6-v2", target_dir=explicit_path)
        mock_st.assert_called_once_with("sentence-transformers/all-MiniLM-L6-v2")
        mock_model.save.assert_called_once_with(explicit_path)
        assert result == explicit_path


def test_download_model_cli_execution():
    """Verify CLI main entrypoint parses arguments and invokes download_model."""
    import sys
    mock_model = MagicMock()
    with patch.object(sys, "argv", ["download_model.py", "test-model", "/tmp/model_out"]), \
         patch("scripts.download_model.SentenceTransformer", return_value=mock_model):
        from scripts.download_model import download_model as dl
        result = dl(sys.argv[1], sys.argv[2])
        assert result == "/tmp/model_out"
