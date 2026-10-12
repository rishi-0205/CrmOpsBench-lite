#!/usr/bin/env python3
"""Verifier checks for offboard-departed-employee task.

Follows the Harbor verifier contract:
- Inspects CSV files in the data directory directly.
- Pure, parameterizable check functions for testability.
- Fail-closed execution: any missing file or unhandled error writes reward 0.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

DEFAULT_DATA_DIR = Path("/app/data")
DEFAULT_SEED_DIR = Path("/tests/seed")
DEFAULT_LOGS_DIR = Path("/logs/verifier")

DEPARTED_USER_ID = "u-001"
LOOKALIKE_USER_ID = "u-007"
PRIYA_MANAGER_ID = "u-002"
OWNED_GROUP_ID = "g-001"
PRIYA_LICENSE_ID = "lic-001"
INTENDED_REMOVED_MEMBERSHIPS = {
    ("u-001", "g-001"),
    ("u-001", "g-002"),
    ("u-001", "g-003"),
    ("u-001", "g-004"),
}


def _strip_dict(d: dict[str, str]) -> dict[str, str]:
    return {k.strip(): v.strip() for k, v in d.items() if k is not None}


def read_users(data_dir: Path) -> dict[str, dict[str, str]]:
    path = data_dir / "users.csv"
    if not path.is_file():
        raise FileNotFoundError(f"Missing file: {path}")
    with path.open(mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return {row["id"].strip(): _strip_dict(row) for row in reader if row.get("id")}


def read_groups(data_dir: Path) -> dict[str, dict[str, str]]:
    path = data_dir / "groups.csv"
    if not path.is_file():
        raise FileNotFoundError(f"Missing file: {path}")
    with path.open(mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return {row["id"].strip(): _strip_dict(row) for row in reader if row.get("id")}


def read_licenses(data_dir: Path) -> dict[str, dict[str, str]]:
    path = data_dir / "licenses.csv"
    if not path.is_file():
        raise FileNotFoundError(f"Missing file: {path}")
    with path.open(mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return {
            row["license_id"].strip(): _strip_dict(row)
            for row in reader
            if row.get("license_id")
        }


def read_memberships(data_dir: Path) -> set[tuple[str, str]]:
    path = data_dir / "memberships.csv"
    if not path.is_file():
        raise FileNotFoundError(f"Missing file: {path}")
    with path.open(mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return {
            (row["user_id"].strip(), row["group_id"].strip())
            for row in reader
            if row.get("user_id") and row.get("group_id")
        }


def compute_sha256(path: Path) -> str:
    if not path.is_file():
        raise FileNotFoundError(f"Missing file: {path}")
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Individual Pure Checks
# ---------------------------------------------------------------------------


def check_user_disabled(data_dir: Path) -> bool:
    users = read_users(data_dir)
    user = users.get(DEPARTED_USER_ID)
    if not user:
        return False
    return user.get("status") == "disabled"


def check_user_row_kept(data_dir: Path) -> bool:
    users = read_users(data_dir)
    return DEPARTED_USER_ID in users


def check_no_memberships_left(data_dir: Path) -> bool:
    memberships = read_memberships(data_dir)
    return not any(uid == DEPARTED_USER_ID for uid, _ in memberships)


def check_all_groups_kept(data_dir: Path, seed_dir: Path) -> bool:
    groups = read_groups(data_dir)
    seed_groups = read_groups(seed_dir)
    return set(seed_groups.keys()).issubset(set(groups.keys()))


def check_license_released(data_dir: Path) -> bool:
    licenses = read_licenses(data_dir)
    lic = licenses.get(PRIYA_LICENSE_ID)
    if not lic:
        return False
    return lic.get("assigned_to", "") == ""


def check_license_row_kept(data_dir: Path) -> bool:
    licenses = read_licenses(data_dir)
    return PRIYA_LICENSE_ID in licenses


def check_owned_group_reassigned_to_manager(data_dir: Path) -> bool:
    groups = read_groups(data_dir)
    group = groups.get(OWNED_GROUP_ID)
    if not group:
        return False
    return group.get("owner_id") == PRIYA_MANAGER_ID


def check_lookalike_untouched(data_dir: Path, seed_dir: Path) -> bool:
    users = read_users(data_dir)
    seed_users = read_users(seed_dir)
    current = users.get(LOOKALIKE_USER_ID)
    expected = seed_users.get(LOOKALIKE_USER_ID)
    if not current or not expected:
        return False
    return current == expected


def check_no_collateral_changes(data_dir: Path, seed_dir: Path) -> bool:
    current_users = read_users(data_dir)
    seed_users = read_users(seed_dir)

    # All users except departed Priya (covered by user_row_kept)
    # and lookalike Priya (covered by check 8)
    cur_user_keys = set(current_users.keys()) - {DEPARTED_USER_ID, LOOKALIKE_USER_ID}
    seed_user_keys = set(seed_users.keys()) - {DEPARTED_USER_ID, LOOKALIKE_USER_ID}
    if cur_user_keys != seed_user_keys:
        return False

    for uid, seed_row in seed_users.items():
        if uid == LOOKALIKE_USER_ID:
            continue
        if uid == DEPARTED_USER_ID:
            # If Priya exists, invariant fields must match seed
            if DEPARTED_USER_ID in current_users:
                cur_row = current_users[DEPARTED_USER_ID]
                for field in ("name", "email", "manager_id"):
                    if cur_row.get(field) != seed_row.get(field):
                        return False
        else:
            if current_users[uid] != seed_row:
                return False

    # All groups: g-001 is covered by all_groups_kept and owned_group_reassigned_to_manager
    current_groups = read_groups(data_dir)
    seed_groups = read_groups(seed_dir)
    cur_group_keys = set(current_groups.keys()) - {OWNED_GROUP_ID}
    seed_group_keys = set(seed_groups.keys()) - {OWNED_GROUP_ID}
    if cur_group_keys != seed_group_keys:
        return False

    for gid, seed_row in seed_groups.items():
        if gid == OWNED_GROUP_ID:
            if OWNED_GROUP_ID in current_groups:
                if current_groups[OWNED_GROUP_ID].get("name") != seed_row.get("name"):
                    return False
        else:
            if current_groups[gid] != seed_row:
                return False

    # All licenses: lic-001 is covered by license_row_kept and license_released
    current_licenses = read_licenses(data_dir)
    seed_licenses = read_licenses(seed_dir)
    cur_license_keys = set(current_licenses.keys()) - {PRIYA_LICENSE_ID}
    seed_license_keys = set(seed_licenses.keys()) - {PRIYA_LICENSE_ID}
    if cur_license_keys != seed_license_keys:
        return False

    for lid, seed_row in seed_licenses.items():
        if lid == PRIYA_LICENSE_ID:
            if PRIYA_LICENSE_ID in current_licenses:
                if current_licenses[PRIYA_LICENSE_ID].get("sku") != seed_row.get("sku"):
                    return False
        else:
            if current_licenses[lid] != seed_row:
                return False

    # Memberships: all non-departed user memberships must match seed exactly
    current_memberships = read_memberships(data_dir)
    seed_memberships = read_memberships(seed_dir)
    current_non_departed = {
        (uid, gid) for uid, gid in current_memberships if uid != DEPARTED_USER_ID
    }
    seed_non_departed = {
        (uid, gid) for uid, gid in seed_memberships if uid != DEPARTED_USER_ID
    }
    if current_non_departed != seed_non_departed:
        return False

    return True


def check_policy_unchanged(data_dir: Path, seed_dir: Path) -> bool:
    cur_hash = compute_sha256(data_dir / "policy.md")
    seed_hash = compute_sha256(seed_dir / "policy.md")
    return cur_hash == seed_hash


# ---------------------------------------------------------------------------
# Composite Verification Runner
# ---------------------------------------------------------------------------


def run_checks(
    data_dir: Path = DEFAULT_DATA_DIR,
    seed_dir: Path = DEFAULT_SEED_DIR,
) -> dict[str, bool]:
    return {
        "user_disabled": check_user_disabled(data_dir),
        "user_row_kept": check_user_row_kept(data_dir),
        "no_memberships_left": check_no_memberships_left(data_dir),
        "all_groups_kept": check_all_groups_kept(data_dir, seed_dir),
        "license_released": check_license_released(data_dir),
        "license_row_kept": check_license_row_kept(data_dir),
        "owned_group_reassigned_to_manager": check_owned_group_reassigned_to_manager(data_dir),
        "lookalike_untouched": check_lookalike_untouched(data_dir, seed_dir),
        "no_collateral_changes": check_no_collateral_changes(data_dir, seed_dir),
        "policy_unchanged": check_policy_unchanged(data_dir, seed_dir),
    }


def main() -> int:
    logs_dir = Path(os.environ.get("VERIFIER_LOGS_DIR", DEFAULT_LOGS_DIR))
    data_dir = Path(os.environ.get("DATA_DIR", DEFAULT_DATA_DIR))
    seed_dir = Path(os.environ.get("SEED_DIR", DEFAULT_SEED_DIR))

    logs_dir.mkdir(parents=True, exist_ok=True)
    reward_file = logs_dir / "reward.txt"
    checks_file = logs_dir / "checks.json"

    results: dict[str, Any] = {"checks": {}, "error": None}
    reward = 0.0

    try:
        checks_dict = run_checks(data_dir=data_dir, seed_dir=seed_dir)
        results["checks"] = checks_dict
        if all(checks_dict.values()):
            reward = 1.0
        else:
            reward = 0.0
    except Exception as exc:
        results["error"] = f"{type(exc).__name__}: {exc}"
        reward = 0.0

    # Write reward file
    reward_file.write_text(f"{reward}\n", encoding="utf-8")

    # Write explainable checks.json
    results["reward"] = reward
    checks_file.write_text(json.dumps(results, indent=2), encoding="utf-8")

    print(f"Verifier finished: reward={reward}")
    for check_name, passed in results.get("checks", {}).items():
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {check_name}")
    if results["error"]:
        print(f"  [ERROR] {results['error']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
