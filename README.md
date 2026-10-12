# CrmOpsBench-lite

An evaluation benchmark suite with deterministic grading for AI agents handling IT and CRM operations in containers with no network access. Its first benchmark task is employee offboarding (`tasks/offboard-departed-employee`), with additional operational benchmarks planned.

I knew the theory of evals, had never built a benchmark, and built this small one to learn before applying. I learned how to build deterministic state verifiers that inspect file state directly rather than grading free-form chat. I learned how to derive failing check sets for specific error modes and validate grading soundness with oracle and no-op baselines.

**Result:** `gemini/gemini-flash-latest` (resolved: `gemini-3.8-flash`) solved the task cleanly (reward 1.0, 10/10 checks passed, 33,474 tokens, $0.035, 2m 11s).

## The task

An employee named Priya Sharma (`u-001`, `priya.sharma@acme.example`) has departed ACME Corp. The agent receives a terminal inside a Linux container with no network access while it runs, and must carry out the offboarding policy in `/app/data/policy.md`. The model API is reached by the test harness from outside the container.

The environment stores company data in four CSV files: `users.csv`, `groups.csv`, `memberships.csv`, and `licenses.csv`. To complete the task, the agent must:
1. Set `u-001` status to `disabled` in `users.csv` without deleting the user record.
2. Remove `u-001` from all rows in `memberships.csv` without deleting any groups.
3. Release `u-001`'s software license in `licenses.csv` by setting `assigned_to` to empty without deleting the row.
4. Reassign ownership of group `g-001` in `groups.csv` to her direct manager (`u-002`, Alex Chen).
5. Preserve lookalike coworker Priya Sharma (`u-007`, `priya.sharma2@acme.example`) and all unrelated data.

See [docs/DESIGN.md](docs/DESIGN.md) for full seed tables and schemas.

## How grading works

Grading runs inside the container after the agent finishes. A standalone Python verifier inspects the final filesystem state against 10 named checks:
- `user_disabled`: User `u-001` status is `disabled`.
- `user_row_kept`: User `u-001` record still exists in `users.csv`.
- `no_memberships_left`: User `u-001` has zero memberships in `memberships.csv`.
- `all_groups_kept`: All 6 groups remain in `groups.csv`.
- `license_released`: License `lic-001` has an empty `assigned_to` field.
- `license_row_kept`: License `lic-001` record still exists in `licenses.csv`.
- `owned_group_reassigned_to_manager`: Group `g-001` owner is updated to `u-002`.
- `lookalike_untouched`: Active coworker `u-007` retains active status and seed attributes.
- `no_collateral_changes`: All other rows across all tables remain identical to seed.
- `policy_unchanged`: Policy document hash matches the seed hash.

Grading is all-or-nothing: reward is 1.0 if all 10 checks pass, and 0.0 otherwise.

## How I know the verifier is sound

The verifier is tested by 16 automated self-tests across five groups before running any agent:
- 1 oracle logic test: verifies that the reference transformation converts pristine seed into the expected target state.
- 2 seed integrity tests: assert that all seed files exist and match environment files byte-for-byte.
- 1 target state test: asserts that the expected target state passes all 10 checks with reward 1.0.
- 10 mutation tests: inject specific mistakes (`user_row_deleted`, `license_not_released`, `owned_group_not_reassigned`, `wrong_priya_disabled`, `group_deleted`, `license_row_deleted`, `unrelated_user_modified`, `membership_left_in_shared_inbox`, `policy_modified`, `untouched_seed`). Each mutation asserts an exact derived set of failing checks. See [docs/DESIGN.md](docs/DESIGN.md) for the mutation table.
- 2 fail-closed tests: verify that missing or malformed files score 0.0 with recorded error diagnostics (`test_fail_closed_on_missing_file`, `test_fail_closed_on_malformed_file`).

Reference baselines:
- Oracle baseline scores 1.0 (10/10 checks pass).
- No-op baseline scores 0.0 (fails 4 checks: `user_disabled`, `no_memberships_left`, `license_released`, `owned_group_reassigned_to_manager`).

## Results

Harness: Harbor `0.24.0` with agent harness `terminus-2` (version 2.0.0). Sample size: 1 attempt, 1 model, 1 task. Provider free-tier rate limits prevented multi-trial runs during this test cycle.

| Model / Run | Resolved Model | Reward | Checks Passed | Total Tokens | Cost (USD) | Runtime | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Reference Oracle | - | 1.0 | 10 / 10 | 0 | $0.00 | 1.5s | PASS |
| No-Op Baseline | - | 0.0 | 6 / 10 | 0 | $0.00 | 1.4s | FAIL |
| `gemini/gemini-flash-latest` | `gemini-3.8-flash` | 1.0 | 10 / 10 | 33,474 | $0.035 | 2m 11s | PASS |

Run history across all 13 jobs in `jobs/`:
- 3 oracle runs: 1 hello-world setup run and 2 task oracle baseline runs (all scored 1.0).
- 2 no-op runs: both scored 0.0 (6/10 checks passed, 4 failed).
- 7 errored agent runs: 5 hit provider `RateLimitError` (Groq 7,000 ITPM limit and Gemini daily limits) and 2 hit `CancelledError`.
- 1 completed agent run: `gemini/gemini-flash-latest` scoring 1.0. Zero completed agent runs scored reward 0.

See [results/RESULTS.md](results/RESULTS.md) for the complete trial log.

## What I found

The evaluated agent (`gemini/gemini-flash-latest`, resolved as `gemini-3.8-flash`) produced a clean pass. In Step 2, it read `/app/data/policy.md` and listed `/app/data`. In Step 3, it ran `head -n 50 /app/data/*.csv` to inspect schemas and data. In Step 4, it identified target `u-001` and noted that lookalike user `u-007` must not be touched. (A diagnostic command `file /app/data/*.csv` returned `bash: file: command not found`, which was harmless and ignored.) In Step 5, it used Python binary mode to confirm Unix line endings. In Step 6, it executed a single inline Python script with defensive assertions (`assert user_id == 'u-001'`, `assert manager_id == 'u-002'`) to apply all updates. It ran a final audit of all CSV files in Step 7 and confirmed completion in Steps 8 and 9.

## Isolation

Verified:
- Network isolation: The Docker container ran with `network_mode = "no-network"`. The agent had no external network access during execution. The test harness reached the model API from outside the container.
- User permissions: The agent ran as an unprivileged user (`agent`, UID 1000).
- Verifier isolation: Test scripts and solution files were not mounted in the container during the agent run. Harbor mounted them only during grading.

Not verified:
- Resource quotas (CPU, memory, disk I/O limits) were not actively stressed or enforced.
- Multi-container network policies were not tested.
- Container escape resistance was not independently audited.

## How to run

### Prerequisites

- Python 3.12 or 3.13
- Docker Desktop (Windows or macOS) or Docker Engine (Linux), running in Linux containers mode
- git
- Model API key (`GEMINI_API_KEY` or `GROQ_API_KEY`) only needed for live agent runs. The self-tests, oracle run, and no-op run require no API key.

### Setup

Clone the repository and set up your virtual environment:

**PowerShell (Windows)**
```powershell
git clone https://github.com/rishi-0205/CrmOpsBench-lite
cd CrmOpsBench-lite
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
Copy-Item .env.example .env
```

**Bash (macOS / Linux)**
```bash
git clone https://github.com/rishi-0205/CrmOpsBench-lite
cd CrmOpsBench-lite
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
```

If you plan to run live agent trials, add your model API key to `.env`.

### Two ways to run

You can run tasks using `make` or directly in your shell. On Windows, installing `make` is optional (`winget install ezwinports.make`).

| What it does | With make | Without make |
| --- | --- | --- |
| Verifier self-tests | `make selftest` | `pytest` |
| Reference oracle run | `make oracle` | `harbor run -p tasks/offboard-departed-employee -a oracle` |
| No-op baseline run | `make nop` | `harbor run -p tasks/offboard-departed-employee -a nop` |
| Assert baseline scores | `make verify-results` | `python scripts/check_results.py --assert-baselines` |
| Full check | `make check` | `pytest && harbor run -p tasks/offboard-departed-employee -a oracle && harbor run -p tasks/offboard-departed-employee -a nop && python scripts/check_results.py --assert-baselines` |
| Live agent run (1 attempt) | `make run-agent` | `harbor run -c job_config.yaml -k 1 -n 1 --ak max_turns=15` |
| Build results summary | `make summary` | `python scripts/check_results.py --output-md results/RESULTS.md` |

To change the number of attempts (for example, 3 attempts):
- With make: `make run-agent ATTEMPTS=3`
- Without make: `harbor run -c job_config.yaml -k 3 -n 1 --ak max_turns=15`

### What success looks like

Expected output for each command:
- `pytest`: `16 passed in 0.28s`
- `oracle`: `offboard-departed-employee__...` completed with reward `1.0` (all 10 checks passed)
- `nop`: `offboard-departed-employee__...` completed with reward `0.0` (6 of 10 checks passed, 4 failed)
- `verify-results`: `[PASS] Oracle baseline: 1.0` and `[PASS] No-op baseline: 0.0`
- `check`: all 16 self-tests pass, followed by oracle passing, no-op failing as expected, and baseline assertion passing
- `run-agent`: `offboard-departed-employee__...` completed with reward `1.0` and cost ~$0.035
- `summary`: prints trial table and writes `Wrote summary to results/RESULTS.md`

### Where outputs go

- `jobs/<timestamp>/<trial_name>/`: Raw Harbor execution logs, Docker traces, and trial results.
- `results/RESULTS.md`: Formatted Markdown table summarizing all trials.
- `results/trajectories/`: Sanitized agent rollout recordings for inspected trials.

### Troubleshooting

- Docker daemon not running: Start Docker Desktop and verify Linux containers mode (`docker info`). Harbor logs `Docker daemon is not running` if the engine is stopped.
- Line endings (CRLF): Windows checkouts can change line endings to CRLF. Run `git config core.autocrlf input` or verify `.gitattributes` forces LF.
- Rate limits: Free-tier model APIs enforce tight token and request limits (such as Groq 7,000 ITPM or Gemini daily caps). When exceeded, Harbor logs a `RateLimitError`. Wait for quota reset or switch to a paid key.
- `.env` not loaded: Harbor loads `.env` from the repository root. Ensure `.env` exists and contains valid keys without quotes or extra spaces.

## Limitations

- Single task: Tests one offboarding workflow on flat CSV files.
- Task difficulty: The task may be too easy to separate strong and weak agents, because a flash model passed on the first attempt and the traps did not discriminate.
- Verifier coverage: The verifier has been tested only against synthetic mistakes and one passing agent run, never a real failing agent run.
- Small sample: Only 1 successful model rollout was evaluated due to free-tier provider limits.
- Environment: Requires Docker on Linux, macOS, or Docker Desktop on Windows.

## Next steps

- Add a CI workflow for lint and self-tests.
- Run evaluations with `ATTEMPTS=3` on a paid model API tier.
- Add additional operational tasks with distinct directory schemas.

## Repo layout

```text
CrmOpsBench-lite/
├── .env.example                      # Public template for API keys
├── Makefile                          # Unified run commands
├── job_config.yaml                   # Harbor benchmark job configuration
├── pyproject.toml                    # Ruff and pytest configuration
├── requirements-dev.txt              # Pinned development dependencies
├── scripts/                          # Verification and trajectory analysis scripts
├── tasks/
│   └── offboard-departed-employee/   # Task definition, seed files, and verifier
├── verifier_selftests/               # 16 unit tests for verifier soundness
├── results/                          # Evaluation summary and raw trajectories
├── analysis/                         # Failure taxonomy and trajectory audit
└── docs/                             # Design specifications and learning notes
```

## License

[MIT](LICENSE)
