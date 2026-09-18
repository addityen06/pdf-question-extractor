"""
Pytest configuration and shared fixtures.
"""
from __future__ import annotations

import pytest
from pathlib import Path


@pytest.fixture
def fixtures_dir() -> Path:
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_pdf(fixtures_dir: Path) -> Path:
    """
    Path to the sample PDF fixture used for integration tests.
    Place a test PDF at tests/fixtures/sample_paper.pdf before running
    integration tests.
    """
    p = fixtures_dir / "sample_paper.pdf"
    if not p.exists():
        pytest.skip("Sample PDF fixture not available")
    return p
