from __future__ import annotations

import hashlib
from pathlib import Path

REQUIRED_FILES = [
    "users.csv",
    "groups.csv",
    "memberships.csv",
    "licenses.csv",
    "policy.md",
]


def _file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()


def test_seed_and_environment_files_exist(env_data_dir: Path, seed_dir: Path) -> None:
    for filename in REQUIRED_FILES:
        env_file = env_data_dir / filename
        seed_file = seed_dir / filename
        assert env_file.is_file(), f"Environment data file missing: {env_file}"
        assert seed_file.is_file(), f"Seed data file missing: {seed_file}"
        assert env_file.stat().st_size > 0, f"Environment file empty: {env_file}"
        assert seed_file.stat().st_size > 0, f"Seed file empty: {seed_file}"


def test_seed_and_environment_byte_exact_equality(env_data_dir: Path, seed_dir: Path) -> None:
    for filename in REQUIRED_FILES:
        env_file = env_data_dir / filename
        seed_file = seed_dir / filename
        env_hash = _file_hash(env_file)
        seed_hash = _file_hash(seed_file)
        assert (
            env_hash == seed_hash
        ), f"Checksum mismatch for {filename}: env={env_hash} != seed={seed_hash}"
