"""
Unit tests corresponding 1:1 to src/config.py:
- Settings class instantiation and default values
- Path resolution (project_root, raw_catalog_path)
- Scoring weights (default_alpha + default_beta == 1.0)
- Service SLA latency budget (50.0ms)
- Primary physical specification key
"""

import pytest
from config import settings


def test_settings_paths():
    """Verify project root and raw catalog path resolution."""
    assert settings.project_root.exists()
    assert settings.project_root.is_dir()
    assert settings.raw_catalog_path.exists()
    assert settings.raw_catalog_path.is_file()


def test_settings_scoring_weights():
    """Verify default composite ranking hyperparameters sum to 1.0."""
    assert settings.default_alpha == 0.7
    assert settings.default_beta == 0.3
    assert (settings.default_alpha + settings.default_beta) == pytest.approx(1.0)


def test_settings_sla_and_spec_key():
    """Verify latency threshold and primary spec key defaults."""
    assert settings.sla_max_latency_ms == 50.0
    assert settings.primary_spec_key == "collar_diameter"
    assert settings.data_source == "json"


def test_package_version():
    """Verify root package exposes standard __version__ metadata."""
    import src
    assert src.__version__ == "0.1.0"


