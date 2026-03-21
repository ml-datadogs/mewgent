from __future__ import annotations

from pathlib import Path

import pytest

from src.data.save_reader import SaveData, read_save

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def save_data() -> SaveData:
    """Parse the test save file once and share across all tests."""
    return read_save(FIXTURES_DIR / "steamcampaign03.sav")
