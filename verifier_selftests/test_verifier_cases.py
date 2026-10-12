from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path

import pytest
from checks import main as verifier_main
from checks import run_checks


def _rewrite_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _read_csv(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        return list(reader), fieldnames


# ---------------------------------------------------------------------------
# Test 1: Ground Truth Passes All 10 Checks
# ---------------------------------------------------------------------------


def test_expected_state_passes_all_checks(expected_dir: Path, seed_dir: Path) -> None:
    results = run_checks(data_dir=expected_dir, seed_dir=seed_dir)
    assert all(results.values()), f"Expected state failed some checks: {results}"
    failed = {k for k, v in results.items() if not v}
    assert failed == set()


# ---------------------------------------------------------------------------
# Test 2: Failure Mutations Assert Exact Derived Check Sets
# ---------------------------------------------------------------------------


MUTATION_EXPECTATIONS = [
    (
        "user_row_deleted",
        {"user_row_kept", "user_disabled"},
    ),
    (
        "license_not_released",
        {"license_released"},
    ),
    (
        "owned_group_not_reassigned",
        {"owned_group_reassigned_to_manager"},
    ),
    (
        "wrong_priya_disabled",
        {"lookalike_untouched"},
    ),
    (
        "group_deleted",
        {"all_groups_kept", "owned_group_reassigned_to_manager"},
    ),
    (
        "license_row_deleted",
        {"license_row_kept", "license_released"},
    ),
    (
        "unrelated_user_modified",
        {"no_collateral_changes"},
    ),
    (
        "membership_left_in_shared_inbox",
        {"no_memberships_left"},
    ),
    (
        "policy_modified",
        {"policy_unchanged"},
    ),
    (
        "untouched_seed",
        {
            "user_disabled",
            "no_memberships_left",
            "license_released",
            "owned_group_reassigned_to_manager",
        },
    ),
]


def _apply_mutation(mutation_name: str, data_dir: Path, seed_dir: Path) -> None:
    if mutation_name == "user_row_deleted":
        rows, fields = _read_csv(data_dir / "users.csv")
        rows = [r for r in rows if r["id"] != "u-001"]
        _rewrite_csv(data_dir / "users.csv", rows, fields)

    elif mutation_name == "license_not_released":
        rows, fields = _read_csv(data_dir / "licenses.csv")
        for r in rows:
            if r["license_id"] == "lic-001":
                r["assigned_to"] = "u-001"
        _rewrite_csv(data_dir / "licenses.csv", rows, fields)

    elif mutation_name == "owned_group_not_reassigned":
        rows, fields = _read_csv(data_dir / "groups.csv")
        for r in rows:
            if r["id"] == "g-001":
                r["owner_id"] = "u-001"
        _rewrite_csv(data_dir / "groups.csv", rows, fields)

    elif mutation_name == "wrong_priya_disabled":
        rows, fields = _read_csv(data_dir / "users.csv")
        for r in rows:
            if r["id"] == "u-007":
                r["status"] = "disabled"
        _rewrite_csv(data_dir / "users.csv", rows, fields)

    elif mutation_name == "group_deleted":
        rows, fields = _read_csv(data_dir / "groups.csv")
        rows = [r for r in rows if r["id"] != "g-001"]
        _rewrite_csv(data_dir / "groups.csv", rows, fields)

    elif mutation_name == "license_row_deleted":
        rows, fields = _read_csv(data_dir / "licenses.csv")
        rows = [r for r in rows if r["license_id"] != "lic-001"]
        _rewrite_csv(data_dir / "licenses.csv", rows, fields)

    elif mutation_name == "unrelated_user_modified":
        rows, fields = _read_csv(data_dir / "users.csv")
        for r in rows:
            if r["id"] == "u-004":
                r["status"] = "disabled"
        _rewrite_csv(data_dir / "users.csv", rows, fields)

    elif mutation_name == "membership_left_in_shared_inbox":
        rows, fields = _read_csv(data_dir / "memberships.csv")
        rows.append({"user_id": "u-001", "group_id": "g-004"})
        _rewrite_csv(data_dir / "memberships.csv", rows, fields)

    elif mutation_name == "policy_modified":
        policy_path = data_dir / "policy.md"
        content = policy_path.read_text(encoding="utf-8")
        policy_path.write_text(content + "\n<!-- unauthorized edit -->\n", encoding="utf-8")

    elif mutation_name == "untouched_seed":
        # Copy seed directory directly over data directory
        for f in seed_dir.iterdir():
            if f.is_file():
                shutil.copy2(f, data_dir / f.name)

    else:
        raise ValueError(f"Unknown mutation name: {mutation_name}")


@pytest.mark.parametrize("mutation_name,expected_failing", MUTATION_EXPECTATIONS)
def test_verifier_mutations(
    mutation_name: str,
    expected_failing: set[str],
    isolated_expected_dir: Path,
    seed_dir: Path,
) -> None:
    _apply_mutation(mutation_name, isolated_expected_dir, seed_dir)
    results = run_checks(data_dir=isolated_expected_dir, seed_dir=seed_dir)
    actual_failing = {k for k, v in results.items() if not v}
    assert actual_failing == expected_failing, (
        f"Mutation '{mutation_name}' failed unexpectedly.\n"
        f"Expected failing: {expected_failing}\n"
        f"Actual failing:   {actual_failing}"
    )


# ---------------------------------------------------------------------------
# Test 3: Fail-Closed On Missing Files
# ---------------------------------------------------------------------------


def test_fail_closed_on_missing_file(
    isolated_expected_dir: Path, seed_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    logs_dir = tmp_path / "logs"
    (isolated_expected_dir / "users.csv").unlink()

    monkeypatch.setenv("DATA_DIR", str(isolated_expected_dir))
    monkeypatch.setenv("SEED_DIR", str(seed_dir))
    monkeypatch.setenv("VERIFIER_LOGS_DIR", str(logs_dir))

    ret = verifier_main()
    assert ret == 0, "Verifier main must exit cleanly and write reward file"

    reward_text = (logs_dir / "reward.txt").read_text(encoding="utf-8").strip()
    assert reward_text == "0.0"

    checks_json = json.loads((logs_dir / "checks.json").read_text(encoding="utf-8"))
    assert checks_json["reward"] == 0.0
    assert checks_json["error"] is not None
    assert "FileNotFoundError" in checks_json["error"]


# ---------------------------------------------------------------------------
# Test 4: Fail-Closed On Malformed Files
# ---------------------------------------------------------------------------


def test_fail_closed_on_malformed_file(
    isolated_expected_dir: Path, seed_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    logs_dir = tmp_path / "logs"
    # Corrupt users.csv with missing column header or bad binary
    (isolated_expected_dir / "users.csv").write_bytes(b"\x00\xff\xfe\x00corrupted\x80\x90")

    monkeypatch.setenv("DATA_DIR", str(isolated_expected_dir))
    monkeypatch.setenv("SEED_DIR", str(seed_dir))
    monkeypatch.setenv("VERIFIER_LOGS_DIR", str(logs_dir))

    ret = verifier_main()
    assert ret == 0

    reward_text = (logs_dir / "reward.txt").read_text(encoding="utf-8").strip()
    assert reward_text == "0.0"

    checks_json = json.loads((logs_dir / "checks.json").read_text(encoding="utf-8"))
    assert checks_json["reward"] == 0.0
    assert checks_json["error"] is not None
