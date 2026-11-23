from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from elections import db
from elections.sources import medsl

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture
def overrides() -> dict[tuple[str, int, str], int]:
    return medsl.load_overrides(ROOT / "data" / "special_seats.json")


@pytest.fixture
def fixes() -> dict[tuple, str]:
    return medsl.load_fixes(ROOT / "data" / "medsl_fixes.json")


@pytest.fixture
def con() -> sqlite3.Connection:
    c = db.connect(":memory:")
    db.init(c)
    return c
