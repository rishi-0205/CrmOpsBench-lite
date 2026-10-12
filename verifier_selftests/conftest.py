from __future__ import annotations

import shutil
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
TASK_DIR = REPO_ROOT / "tasks" / "offboard-departed-employee"
ENV_DATA_DIR = TASK_DIR / "environment" / "data"
TESTS_DIR = TASK_DIR / "tests"
SEED_DIR = TESTS_DIR / "seed"
EXPECTED_DIR = TESTS_DIR / "expected"


@pytest.fixture
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture
def env_data_dir() -> Path:
    return ENV_DATA_DIR


@pytest.fixture
def seed_dir() -> Path:
    return SEED_DIR


@pytest.fixture
def expected_dir() -> Path:
    return EXPECTED_DIR


@pytest.fixture
def isolated_expected_dir(tmp_path: Path) -> Path:
    target = tmp_path / "data"
    shutil.copytree(EXPECTED_DIR, target)
    return target


@pytest.fixture
def isolated_seed_dir(tmp_path: Path) -> Path:
    target = tmp_path / "data"
    shutil.copytree(SEED_DIR, target)
    return target
