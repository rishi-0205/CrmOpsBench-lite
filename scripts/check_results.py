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
    model_name = (
        agent_info.get("model_name")
        or config.get("agent", {}).get("model_name")
        or "unknown"
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
        "model": model_name,
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


def get_trial_status(trial: dict[str, Any]) -> tuple[str, str]:
    """Returns (status_label, details_label)."""
    exc = trial.get("exception")
    if exc:
        exc_type = exc.get("exception_type", "Error") if isinstance(exc, dict) else "Error"
        return f"ERROR ({exc_type})", "Trial hit an unhandled exception or rate limit"

    reward = trial.get("reward", 0.0)
    checks = trial.get("checks", {})
    if reward == 1.0:
        return "PASS", f"{len(checks)}/10 checks passed" if checks else "Reward 1.0"
    else:
        passed = sum(1 for v in checks.values() if v)
        total = len(checks) if checks else 10
        return "FAIL (Reward 0.0)", f"{passed}/{total} checks passed"


def generate_markdown_summary(jobs: list[dict[str, Any]]) -> str:
    all_trials = [t for j in jobs for t in j["trials"]]
    total_count = len(all_trials)
    pass_count = sum(1 for t in all_trials if not t.get("exception") and t.get("reward") == 1.0)
    fail_count = sum(1 for t in all_trials if not t.get("exception") and t.get("reward") != 1.0)
    error_count = sum(1 for t in all_trials if t.get("exception"))

    lines = [
        "# Evaluation Results Summary",
        "",
        f"- **Total Sample Size:** {total_count} trial(s) across {len(jobs)} job(s)",
        f"- **Outcome Counts:** {pass_count}/{total_count} passed, {fail_count}/{total_count} failed (reward 0.0), {error_count}/{total_count} errored",
        "",
        "> Note: For small evaluation samples, results are reported as exact counts rather than percentage estimates.",
        "",
        "| Job / Timestamp | Agent | Model | Trial Name | Reward | Status | Details |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]

    for job in jobs:
        timestamp = job["job_dir"].name
        for trial in job["trials"]:
            status_label, details_label = get_trial_status(trial)
            reward_str = f"{trial['reward']:.1f}"
            lines.append(
                f"| `{timestamp}` | `{trial['agent']}` | `{trial.get('model', '-')}` | `{trial['trial_name']}` | `{reward_str}` | **{status_label}** | {details_label} |"
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

    all_trials = [t for j in jobs for t in j["trials"]]
    total_count = len(all_trials)
    pass_count = sum(1 for t in all_trials if not t.get("exception") and t.get("reward") == 1.0)
    fail_count = sum(1 for t in all_trials if not t.get("exception") and t.get("reward") != 1.0)
    error_count = sum(1 for t in all_trials if t.get("exception"))

    print(f"Found {len(jobs)} jobs ({total_count} total trials) in {args.jobs_dir}:")
    print(f"  Sample summary: {pass_count}/{total_count} passed, {fail_count}/{total_count} failed, {error_count}/{total_count} errored\n")

    latest_oracle_reward: float | None = None
    latest_nop_reward: float | None = None

    for job in jobs:
        print(f"Job: {job['job_dir'].name}")
        for trial in job["trials"]:
            status_label, details_label = get_trial_status(trial)
            print(
                f"  Agent: {trial['agent']} | Model: {trial.get('model')} | Trial: {trial['trial_name']} | Reward: {trial['reward']} | Status: {status_label}"
            )
            if trial["checks"]:
                for cname, cpass in trial["checks"].items():
                    mark = "OK" if cpass else "FAIL"
                    print(f"    [{mark}] {cname}")

            if trial["agent"] == "oracle" and not trial.get("exception"):
                latest_oracle_reward = trial["reward"]
            elif trial["agent"] == "nop" and not trial.get("exception"):
                latest_nop_reward = trial["reward"]

    if args.output_md:
        md_text = generate_markdown_summary(jobs)
        args.output_md.parent.mkdir(parents=True, exist_ok=True)
        args.output_md.write_text(md_text, encoding="utf-8")
        print(f"\nWrote summary to {args.output_md} (Sample size: {total_count} trial(s))")

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
