from __future__ import annotations

import csv
from pathlib import Path


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def test_programmatic_oracle_transforms_seed_to_expected(
    seed_dir: Path, expected_dir: Path
) -> None:
    # 1. Users transformation: u-001 disabled, all other fields/users unchanged
    seed_users = _read_csv_rows(seed_dir / "users.csv")
    expected_users = _read_csv_rows(expected_dir / "users.csv")

    transformed_users = []
    for row in seed_users:
        new_row = dict(row)
        if new_row["id"] == "u-001":
            new_row["status"] = "disabled"
        transformed_users.append(new_row)

    assert (
        transformed_users == expected_users
    ), "Programmatic user transform does not match expected/users.csv"

    # 2. Groups transformation: g-001 transferred to manager u-002
    seed_groups = _read_csv_rows(seed_dir / "groups.csv")
    expected_groups = _read_csv_rows(expected_dir / "groups.csv")

    transformed_groups = []
    for row in seed_groups:
        new_row = dict(row)
        if new_row["id"] == "g-001":
            new_row["owner_id"] = "u-002"
        transformed_groups.append(new_row)

    assert (
        transformed_groups == expected_groups
    ), "Programmatic group transform does not match expected/groups.csv"

    # 3. Licenses transformation: lic-001 unassigned
    seed_licenses = _read_csv_rows(seed_dir / "licenses.csv")
    expected_licenses = _read_csv_rows(expected_dir / "licenses.csv")

    transformed_licenses = []
    for row in seed_licenses:
        new_row = dict(row)
        if new_row["license_id"] == "lic-001":
            new_row["assigned_to"] = ""
        transformed_licenses.append(new_row)

    assert (
        transformed_licenses == expected_licenses
    ), "Programmatic license transform does not match expected/licenses.csv"

    # 4. Memberships transformation: all u-001 rows removed
    seed_memberships = _read_csv_rows(seed_dir / "memberships.csv")
    expected_memberships = _read_csv_rows(expected_dir / "memberships.csv")

    transformed_memberships = [
        dict(row) for row in seed_memberships if row["user_id"] != "u-001"
    ]

    assert (
        transformed_memberships == expected_memberships
    ), "Programmatic membership transform does not match expected/memberships.csv"

    # 5. Policy document: must be unchanged
    seed_policy = (seed_dir / "policy.md").read_text(encoding="utf-8")
    expected_policy = (expected_dir / "policy.md").read_text(encoding="utf-8")
    assert seed_policy == expected_policy, "Policy document mismatch between seed and expected"
