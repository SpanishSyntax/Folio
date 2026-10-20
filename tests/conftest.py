"""Shared fixtures for Folio tests."""

import pytest
from pathlib import Path


@pytest.fixture
def tmp_workspace(tmp_path: Path) -> Path:
    """Provides an isolated workspace directory."""
    return tmp_path
