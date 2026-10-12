#!/usr/bin/env python3
"""Parses and asserts Harbor job evaluation results.

Supports:
- Dynamically discovering all runs in `jobs/`.
- Parsing trial-level `result.json` and `verifier/checks.json`.
- Asserting baseline results (oracle=1.0, nop=0.0).
- Generating Markdown summaries for results documentation.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def parse_trial_dir(trial_dir: Path) -> dict[str, Any] | None:
    result_file = trial_dir / "result.json"
    if not result_file.is_file():
        return None

    try:
        data = json.loads(result_file.read_text(encoding="utf-8"))
    except Exception:
        return None

    agent_info = data.get("agent_info") or {}
    config = data.get("config") or {}
    agent_name = (
        agent_info.get("name")
        or config.get("agent", {}).get("name", "unknown")
    )
    trial_name = data.get("trial_name", trial_dir.name)
    verifier_result = data.get("verifier_result") or {}
    rewards = verifier_result.get("rewards") or {} if isinstance(verifier_result, dict) else {}
    reward = rewards.get("reward", 0.0) if isinstance(rewards, dict) else 0.0
    exception = data.get("exception_info")

    checks_file = trial_dir / "verifier" / "checks.json"
    checks = {}
    if checks_file.is_file():
        try:
            checks_data = json.loads(checks_file.read_text(encoding="utf-8"))
            checks = checks_data.get("checks", {})
        except Exception:
            pass

    return {
        "trial_name": trial_name,
        "agent": agent_name,
        "reward": float(reward) if reward is not None else 0.0,
        "exception": exception,
        "checks": checks,
        "trial_dir": trial_dir,
    }


def parse_job_dir(job_dir: Path) -> dict[str, Any] | None:
    result_file = job_dir / "result.json"
    if not result_file.is_file():
        return None

    try:
        job_data = json.loads(result_file.read_text(encoding="utf-8"))
    except Exception:
        return None

    trials = []
    for item in sorted(job_dir.iterdir()):
        if item.is_dir() and item.name not in ("artifacts",):
            trial_info = parse_trial_dir(item)
            if trial_info:
                trials.append(trial_info)

    return {
        "job_id": job_data.get("id"),
        "job_dir": job_dir,
        "finished_at": job_data.get("finished_at"),
        "trials": trials,
    }


def collect_all_jobs(jobs_root: Path) -> list[dict[str, Any]]:
    if not jobs_root.is_dir():
        return []

    jobs = []
    for item in sorted(jobs_root.iterdir()):
        if item.is_dir():
            parsed = parse_job_dir(item)
            if parsed and parsed["trials"]:
                jobs.append(parsed)
    return jobs


def generate_markdown_summary(jobs: list[dict[str, Any]]) -> str:
    lines = [
        "# Evaluation Results Summary",
        "",
        "| Job / Timestamp | Agent | Trial Name | Reward | Pass / Fail |",
        "| --- | --- | --- | --- | --- |",
    ]

    for job in jobs:
        timestamp = job["job_dir"].name
        for trial in job["trials"]:
            status = "PASS" if trial["reward"] == 1.0 else "FAIL"
            lines.append(
                f"| `{timestamp}` | `{trial['agent']}` | `{trial['trial_name']}` | `{trial['reward']}` | {status} |"
            )

    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Check Harbor benchmark results.")
    parser.add_argument(
        "--jobs-dir",
        type=Path,
        default=Path("jobs"),
        help="Path to the jobs directory (default: jobs)",
    )
    parser.add_argument(
        "--assert-baselines",
        action="store_true",
        help="Assert that latest oracle scored 1.0 and latest nop scored 0.0",
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=None,
        help="Path to write markdown summary",
    )
    args = parser.parse_args()

    jobs = collect_all_jobs(args.jobs_dir)
    if not jobs:
        print(f"No completed jobs found in {args.jobs_dir}")
        return 1

    print(f"Found {len(jobs)} jobs in {args.jobs_dir}:")
    latest_oracle_reward: float | None = None
    latest_nop_reward: float | None = None

    for job in jobs:
        print(f"\nJob: {job['job_dir'].name}")
        for trial in job["trials"]:
            print(
                f"  Agent: {trial['agent']} | Trial: {trial['trial_name']} | Reward: {trial['reward']}"
            )
            if trial["checks"]:
                for cname, cpass in trial["checks"].items():
                    mark = "OK" if cpass else "FAIL"
                    print(f"    [{mark}] {cname}")

            if trial["agent"] == "oracle":
                latest_oracle_reward = trial["reward"]
            elif trial["agent"] == "nop":
                latest_nop_reward = trial["reward"]

    if args.output_md:
        md_text = generate_markdown_summary(jobs)
        args.output_md.parent.mkdir(parents=True, exist_ok=True)
        args.output_md.write_text(md_text, encoding="utf-8")
        print(f"\nWrote summary to {args.output_md}")

    if args.assert_baselines:
        print("\nAsserting baselines:")
        if latest_oracle_reward is None:
            print("ERROR: No oracle trial found.")
            return 1
        if latest_nop_reward is None:
            print("ERROR: No nop trial found.")
            return 1

        assert latest_oracle_reward == 1.0, f"Expected oracle=1.0, got {latest_oracle_reward}"
        assert latest_nop_reward == 0.0, f"Expected nop=0.0, got {latest_nop_reward}"
        print("  [PASS] Oracle baseline: 1.0")
        print("  [PASS] No-op baseline: 0.0")

    return 0


if __name__ == "__main__":
    sys.exit(main())
