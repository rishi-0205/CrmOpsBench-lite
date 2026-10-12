# offboarding-bench Master Plan

## 1. Project Overview and Objective

Build `offboarding-bench`: a single Harbor evaluation task that tests whether an AI agent can correctly offboard a departed employee within a directory stored as plain CSV files inside a Docker container.

- **Task ID:** `offboard-departed-employee`
- **Core Value:** Portfolio benchmark for an evaluation engineering role, focusing on verifier rigor, deterministic grading, trap coverage, and failure explainability.
- **Grading Principle:** State-based grading only. The verifier grades file modifications directly, never the agent's textual claims.
- **Time Budget:** 5 to 6 hours total (accounting for teaching and deep mentorship).
- **Milestone Checkpoint:**
  - **After Phase 4:** The benchmark is scientifically defensible. The verifier self-tests, oracle run (1), and no-op run (0) prove the task and verifier are completely sound.
  - **Phases 5 to 7:** Make the project presentable as a public portfolio piece (agent evaluations, failure taxonomy, CI, and README).

### The Never-Cut Rules
If time runs short, we cut secondary items, but we **never** cut:
1. The verifier self-tests (testing that bad solutions fail on their exact expected set of named checks).
2. The oracle (score 1) and no-op (score 0) checks.
3. The intentional traps (lookalike user, group ownership, audit preservation, distractor licenses).

---

## 2. Working Agreement and Methodology

### Mentorship and Tone
- Senior engineer and patient mentor.
- Short sentences, plain words, no em dashes, no marketing language.
- Never fabricate numbers, logs, or results.

### Setup Workflow (Phase 0)
1. Mentor explains the command, why it is needed, any flags, and what success looks like.
2. User executes the command in PowerShell and pastes terminal output.
3. Mentor reviews and interprets the output line by line. Never assume success.

### Implementation Workflow (Phases 1 to 7)
1. Before writing any file, mentor provides:
   - The concept in plain words (with an analogy if helpful).
   - What we will build and why.
   - Options and trade-offs, with a recommendation.
   - Planned file contents or outline.
2. Mentor stops and waits for user approval.
3. After approval, mentor writes the file.
4. Mentor walks through the code line by line, explains non-obvious details, shows how to verify, and asks ONE comprehension question (for conceptual steps).
5. User answers before moving to the next step.

### Step Batching and Comprehension Rule
- Trivial steps (such as small directory creation or companion file checks) may be combined.
- The comprehension question and the `LEARNING_NOTES.md` entry apply **only** to steps that introduce a new concept. Trivial or repetitive steps do not require a separate question or glossary entry.

### Version Control and Git Remote Protocol
- Small commits with conventional commit messages.
- Each commit message must be proposed and explained by the mentor before the user runs `git commit`.
- A private GitHub repository is created in Phase 0.
- We push to the remote repository after every phase commit.
- Before each commit, mentor and user confirm that `git status` shows no `.env`, `.venv`, or `jobs/`.

### Living Plan and Learning Notes Protocol
- `PLAN.md` is frozen after Phase 0 setup begins. It is modified only when a step is blocked by a real finding. Each change is documented in Section 9 (Plan Change Log).
- Checkboxes in `PLAN.md` are ticked at the end of each phase.
- We do not re-review the entire plan at the start of each phase.
- `docs/LEARNING_NOTES.md` is updated after **every conceptual step**:
  1. Mentor drafts a one-to-two line entry containing the new term and one key takeaway.
  2. Mentor asks the user to restate it in their own words.
  3. Mentor reviews the user's phrasing, corrects any gaps kindly, and saves it.
- After **each phase**, mentor and user add a fuller "what we built and why" summary paragraph.

---

## 3. Technical Constraints and Baseline

- **Host Environment:** Windows 11, PowerShell.
- **Host Python:** Python 3.13.1.
- **Harbor Python Compatibility:** PyPI `harbor` requires Python `>=3.12`. Both Python 3.12 and 3.13 are fully supported.
- **Framework and Tool Pinning:**
  - `requirements-dev.txt`: Pins `harbor` (version confirmed via `pip index versions harbor`), `pytest`, and `ruff`.
  - `requirements-ci.txt`: Pins `pytest` and `ruff` only. CI must never install Harbor.
- **Container Environment:** Linux container with Docker Desktop (Linux mode, WSL2 backend).
- **Container Base Image:** `python:3.12-slim-bookworm` (pinned tag).
- **Line Endings:** `.gitattributes` enforces `* text=auto eol=lf` across the repository to prevent Windows CRLF issues in Linux containers.
- **Core Dependencies:** Python standard library (`csv`, `json`, `pathlib`, `hashlib`), `pytest`, `ruff`. No web frameworks, no Daytona, no cloud dashboard.
- **Secrets Policy:** Never commit secrets. API keys live in `.env` (excluded by `.gitignore`). A `.env.example` file acts as the public template. Scan all saved trajectory files for leaked keys before staging.
- **License:** MIT License (`LICENSE` added in Phase 7).

### Make-Style Targets on Windows: Options and Trade-offs
Since Windows does not ship with GNU Make by default, we have two options:
- **Option 1 (Recommended): Install GNU Make via Windows Package Manager (`winget install ezwinports.make`)**
  - *Trade-off:* Requires a one-time install of a small native Windows tool.
  - *Benefit:* Allows running standard `make check`, `make oracle`, and `make selftest` commands identically to Linux environments and CI.
  - *Windows Rule:* Every recipe in `Makefile` must be a single plain command (no chained `&&`, no Linux shell built-ins like `export` or `rm -rf`).
  - *Prerequisite Rule:* `make check` is built from prerequisites (`check: selftest oracle nop`), not chained inline shell commands.
- **Option 2: Use a Python task runner (e.g. `invoke` or a small `tasks.py`)**
  - *Trade-off:* Diverges from the classic `Makefile` mentioned in the specification.
  - *Benefit:* Works purely within the Python virtual environment without extra OS tools.

*Recommendation:* Option 1 with single plain commands and prerequisite-based chaining.

---

## 4. Key Harbor Framework Discoveries (from Docs)

- **Attempts:** Harbor natively supports multiple attempts via `-k <attempts>` (e.g., `-k 3`) or `n_attempts` in `JobConfig`.
- **Retries:** Harbor natively handles transient retries and exponential backoff via `-r <retries>` and `retry.*` config options.
- **Token and Cost Tracking:** Harbor tracks tokens and cost per trial automatically through LiteLLM and ATIF (`final_metrics`). Cumulative budget stops are checked via output inspection.
- **Test Upload:** Harbor uploads local `tests/` into `/tests/` inside the container after the agent run finishes.
- **Isolation:** `[agent].user` and `[verifier].user` specify unprivileged OS users in `task.toml`.
- **Network Isolation:**
  - **Source Doc:** `https://docs.harborframework.com/tasks/network-policies.md`
  - **Exact Field:** `[agent] network_mode = "no-network"`
  - **Behavior:** `agent.setup()` uses baseline network to install tools, while `agent.run()` enforces `no-network`. Supported on `docker`. Added in Phase 5 after live trial confirmation.
- **Timeouts and Metadata:**
  - **Source Doc:** `https://docs.harborframework.com/tasks/configuration.md`
  - Required schema: `schema_version = "1.3"`.
  - Conservative timeouts: `[verifier] timeout_sec = 120.0`, `[agent] timeout_sec = 300.0`.

---

## 5. Decisions and Open Questions

1. **Seed Facts & Entities:**
   - 12 users, 6 groups, 25 memberships, 8 licenses.
   - Primary keys per file:
     - `users.csv`: `id`
     - `groups.csv`: `id`
     - `licenses.csv`: `license_id`
     - `memberships.csv`: composite key `(user_id, group_id)`
   - Departed employee: Priya Sharma (`priya.sharma@acme.example`, ID `u-001`, manager `Alex Chen` `u-002`).
   - Lookalike user: Priya Sharma (`priya.sharma2@acme.example`, ID `u-007`). She has a different manager (`Marcus Vance`, ID `u-003`) and must remain active and untouched.
   - Departed Priya is a member of 4 groups. One is a shared team inbox group (`Support Inbox`, ID `g-004`) owned by someone else (`Danielle Kim`, ID `u-006`).
   - Departed Priya owns exactly one group (`Platform Engineering`, ID `g-001`). Group ownership must be reassigned to her manager (`Alex Chen`, ID `u-002`).
   - Priya has 1 license assigned that must be released (`assigned_to` cleared).
   - Distractor users and licenses exist to catch careless wildcards.

2. **Native Windows vs. WSL2 Ubuntu Fallback (Open Question):**
   - We will test Harbor natively in Windows PowerShell in Step 0.8.
   - If Harbor CLI, path resolution, or Docker volume mounts fail on Windows, the immediate fallback is WSL2 Ubuntu. This decision is made during Step 0.8.

3. **Model Provider and Endpoint (Open Question):**
   - Kept open until Step 5.0.
   - Step 5.0 will test the provider and key directly with a tiny standalone Python script before Harbor is invoked.
   - If using Modal with Kimi K3, custom auth headers will be tested there. If unsupported by LiteLLM, we fall back to OpenRouter or direct provider key.

4. **Agent User Permissions and Path Verification:**
   - Docker container runs as non-root user `agent` (UID 1000).
   - `/app/data` is owned and writable by `agent` (`chown -R agent:agent /app/data`).
   - In Phase 2 (Step 2.6), we run `docker run` as user `agent` to prove `/tests` and `/solution` do not exist in the image while the agent works.
   - In Phase 4 oracle run, we inspect logs to verify `/tests` appears only during verification time.

5. **Network Access in Container and Fallback:**
   - Network mode is omitted in Phase 2.
   - In Phase 5 (Step 5.4), after a baseline trial, we test `[agent] network_mode = "no-network"`.
   - If the agent harness fails to reach the model API, we fall back to `network_mode = "public"` and document the reason in `README.md`.

6. **Log Retention, Key Scanning, and Trajectory Preservation:**
   - Raw Harbor runs in `jobs/` are excluded by `.gitignore`.
   - Selected sanitized trajectories will be scanned for keys, copied to `results/trajectories/`, and committed.

7. **Phase 6 Evaluation Contingency:**
   - If the agent passes the evaluation trial: we inspect trajectories for near misses and risky commands, test with a weaker model, or add one harder trap. Phase 6 budget is 25 to 30 minutes.

---

## 6. Repository File Layout

```text
offboarding-bench/
├── .env.example
├── .gitattributes            (* text=auto eol=lf)
├── .gitignore
├── .github/
│   └── workflows/
│       └── ci.yml            (runs lint and verifier self-tests using requirements-ci.txt)
├── LICENSE                   (MIT License)
├── Makefile                  (plain single-command recipes, prerequisite-based check)
├── PLAN.md
├── pyproject.toml            (ruff and pytest config, created in Step 3.0)
├── README.md
├── requirements-dev.txt      (pinned harbor, pytest, ruff, created in Phase 0)
├── requirements-ci.txt       (pinned pytest, ruff only, created in Phase 0)
├── analysis/
│   └── FAILURES.md
├── docs/
│   ├── DESIGN.md
│   └── LEARNING_NOTES.md
├── results/
│   ├── RESULTS.md
│   └── trajectories/         (selected sanitized trajectories)
├── scripts/
│   └── check_results.py      (asserts oracle=1, nop=0, builds RESULTS.md)
├── tasks/
│   └── offboard-departed-employee/
│       ├── instruction.md
│       ├── task.toml
│       ├── environment/
│       │   ├── Dockerfile
│       │   └── data/
│       │       ├── users.csv
│       │       ├── groups.csv
│       │       ├── memberships.csv
│       │       ├── licenses.csv
│       │       └── policy.md
│       ├── solution/
│       │   └── solve.sh      (edits /app/data with real shell/python commands, no copying)
│       └── tests/
│           ├── checks.py     (pure functions, parameterizable paths, fail-closed main)
│           ├── test.sh
│           ├── expected/
│           │   ├── users.csv
│           │   ├── groups.csv
│           │   ├── memberships.csv
│           │   └── licenses.csv
│           └── seed/
│               ├── users.csv
│               ├── groups.csv
│               ├── memberships.csv
│               ├── licenses.csv
│               └── policy.md  (baseline for policy_unchanged)
└── verifier_selftests/
    ├── conftest.py
    ├── test_seed_integrity.py (environment/data vs tests/seed)
    ├── test_oracle_logic.py    (applies intended changes in python and compares to expected)
    └── test_verifier_cases.py (asserts exact set of named checks per mutation, fail-closed on malformed/missing)
```

---

## 7. Verifier Specification and Failure Cases

### Architecture of `checks.py`
- Pure functions accepting `data_dir`, `seed_dir`, and `expected_dir` with container defaults (`/app/data`, `/tests/seed`, `/tests/expected`).
- Importable directly by host tests in `verifier_selftests/`.
- `main()` wraps all checks in a top-level try/except block. On any exception or unhandled error, it writes `0` to `/logs/verifier/reward.txt` and an error record to `/logs/verifier/checks.json`.
- Missing row rule: Any check depending on a missing row fails deterministically without throwing uncaught key errors.

### Named Checks in `checks.py`
1. `user_disabled`: Priya's status set to `disabled`.
2. `user_row_kept`: Priya's row still exists in `users.csv` (audit preservation).
3. `no_memberships_left`: Priya is removed from all memberships.
4. `all_groups_kept`: No groups are deleted from `groups.csv`.
5. `license_released`: Priya's license has `assigned_to` cleared.
6. `license_row_kept`: The license row still exists in `licenses.csv`.
7. `owned_group_reassigned_to_manager`: Priya's owned group is transferred to her manager.
8. `lookalike_untouched`: The other Priya Sharma (`priya.sharma2@acme.example`) is completely unchanged.
9. `no_collateral_changes`: Row-by-row comparison keyed by id (or composite key for memberships) that ignores row order, quoting, and edge whitespace. Covers every field not intentionally changed, including Priya's own name, email, and manager_id.
10. `policy_unchanged`: `policy.md` is identical to `tests/seed/policy.md` (hash comparison).

### Failing Cases Tested in Self-Tests
The exact expected set of failing checks per mutation is derived by reasoning and documented in `docs/DESIGN.md` before running the verifier:
1. `user_row_deleted`: Fails on the exact derived check set (including `user_row_kept`).
2. `license_not_released`: Fails on `{"license_released"}`.
3. `owned_group_not_reassigned`: Fails on `{"owned_group_reassigned_to_manager"}`.
4. `wrong_priya_disabled`: Fails on `{"lookalike_untouched"}`.
5. `group_deleted`: Fails on `{"all_groups_kept"}`.
6. `license_row_deleted`: Fails on `{"license_row_kept"}`.
7. `unrelated_user_modified`: Fails on `{"no_collateral_changes"}`.
8. `untouched_seed`: Fails on the exact set of unperformed actions (`user_disabled`, `license_released`, `no_memberships_left`, `owned_group_reassigned_to_manager`).
9. `missing_file`: File missing entirely. Fails closed: asserts reward 0 and an error entry in `checks.json`.
10. `malformed_file`: Corrupt CSV syntax. Fails closed: asserts reward 0 and an error entry in `checks.json`.

---

## 8. Phase-by-Phase Roadmap and Execution Tracker

### Status Key
- [x] Completed
- [>] In progress / Current step
- [ ] Upcoming

---

### Phase 0: Setup and Environment Verification (Budget: 45 min)
**Done when:** Virtual environment is active, Git is initialized, Docker is confirmed running in Linux mode with WSL2, Harbor is confirmed with `pip index versions harbor` and installed, `requirements-dev.txt` and `requirements-ci.txt` are created with pinned versions, private GitHub repo is created, hello-world passes, blank task is inspected outside repo and deleted, LEARNING_NOTES.md has Phase 0 summary, initial Git commit is made and pushed.
- [x] Confirm OS (Windows 11) and Shell (PowerShell).
- [x] Check Python version (Python 3.13.1 confirmed).
- [x] Check Git version (Git 2.41.0 confirmed).
- [x] Create `.gitignore`.
- [x] Create live `PLAN.md`.
- [x] Step 0.1: Create Python virtual environment (`.venv`).
- [x] Step 0.2: Activate virtual environment and verify Python path.
- [x] Step 0.3: Create `.gitattributes` (`* text=auto eol=lf`).
- [x] Step 0.4: Initialize Git repository (`git init`).
- [x] Step 0.5: Check Docker installation, daemon status, Linux containers mode, and WSL2 backend.
- [x] Step 0.6: Run `pip index versions harbor` to confirm versions, install Harbor, and explain pip vs. uv.
- [x] Step 0.7: Create `requirements-dev.txt` (pinned harbor, pytest, ruff) and `requirements-ci.txt` (pinned pytest, ruff only).
- [x] Step 0.8: Run Harbor hello-world (using `-a oracle` if model key needed; decide on Windows native vs. WSL2 Ubuntu fallback).
- [x] Step 0.9: Run `harbor task init` on a temporary test task *outside the repo*, inspect generated files, and delete it.
- [x] Step 0.10: Create private GitHub repository and set up remote origin.
- [x] Step 0.11: docs/LEARNING_NOTES.md Phase 0 summary ("what we built and why").
- [x] Step 0.12: Confirm `git status` shows no `.env`, `.venv`, or `jobs/`; propose and execute initial commit; push to GitHub.

---

### Phase 1: Task Design and Specification (Budget: 20 min)
**Done when:** `docs/DESIGN.md` contains full seed tables, policy rules, expected final state, exact derived failing check sets per trap; user approves; Phase 1 summary is recorded in `docs/LEARNING_NOTES.md`; committed and pushed.
- [x] Step 1.1: Design seed data rows (12 users, 6 groups, 25 memberships, 8 licenses) with exact keys and relationships.
- [x] Step 1.2: Design intentional traps and derive the exact set of failing check names for each mutation in `docs/DESIGN.md`.
- [x] Step 1.3: Define policy rules (`policy.md`) and concise agent prompt (`instruction.md`).
- [x] Step 1.4: Define exact expected ground-truth final state.
- [x] Step 1.5: Write `docs/DESIGN.md` and review with user.
- [x] Step 1.6: docs/LEARNING_NOTES.md Phase 1 summary ("what we built and why"), propose commit, commit, and push.

---

### Phase 2: Environment and World Setup (Budget: 30 min)
**Done when:** Seed files exist in `environment/data/`, `Dockerfile` builds cleanly with Python 3.12 and non-root `agent` user owning `/app/data`, `task.toml` has conservative timeouts and metadata, container is inspected interactively, agent user is proven unable to read `/tests` or `/solution` via `docker run`; committed and pushed.
- [x] Step 2.1: Write seed data files into `tasks/offboard-departed-employee/environment/data/`.
- [x] Step 2.2: Write `policy.md` and `instruction.md`.
- [x] Step 2.3: Write `Dockerfile` with Python 3.12, unprivileged user `agent` (UID 1000), and `chown -R agent:agent /app/data`.
- [x] Step 2.4: Write `task.toml` with conservative timeouts (`verifier = 120s`, `agent = 300s`), agent user, and required metadata from Harbor docs.
- [x] Step 2.5: Build Docker container and inspect `/app/data` inside.
- [x] Step 2.6: Use `docker run` as user `agent` to prove `/tests` and `/solution` do not exist in the image while the agent works.
- [x] Step 2.7: docs/LEARNING_NOTES.md Phase 2 summary ("what we built and why"), propose commit, commit, and push.

---

### Phase 3: Tooling and Verifier Implementation (Budget: 40 min)
**Done when:** `pyproject.toml` is configured, `checks.py` has parameterizable paths, 10 pure checks (with keyed row comparison), and fail-closed `main()`, `tests/seed/` and `tests/expected/` are populated, `test.sh` exits 0 while writing `reward.txt` and `checks.json`, and verifier user access to `/app/data` and `/logs/verifier` is verified; committed and pushed.
- [x] Step 3.0: Create `pyproject.toml` with `ruff` and `pytest` configurations.
- [x] Step 3.1: Copy pristine seed files and `policy.md` to `tasks/.../tests/seed/`.
- [x] Step 3.2: Create ground-truth files in `tasks/.../tests/expected/`.
- [x] Step 3.3: Implement `checks.py` with parameterizable paths, 10 pure checks, and fail-closed `main()`.
- [x] Step 3.4: Implement `test.sh`, confirm verifier execution user, and verify read access to `/app/data` and write access to `/logs/verifier`.
- [x] Step 3.5: docs/LEARNING_NOTES.md Phase 3 summary ("what we built and why"), propose commit, commit, and push.

---

### Phase 4: Proof, Self-Tests, Oracle, and No-Op (Budget: 35 min)
**Done when:** All `verifier_selftests` pass (seed integrity, programmatic oracle logic, and 10 failure cases asserting exact check sets or fail-closed errors), manual oracle and no-op runs complete, `/tests` visibility is checked in logs, `scripts/check_results.py` is written to match actual output layout and asserts oracle=1 / nop=0; committed and pushed.
- [x] Step 4.1: Implement `verifier_selftests/test_seed_integrity.py` (checks `environment/data` vs `tests/seed`).
- [x] Step 4.2: Implement `verifier_selftests/test_oracle_logic.py` (programmatically applies intended changes and compares to `expected/`).
- [x] Step 4.3: Implement `verifier_selftests/test_verifier_cases.py` (asserts exact check sets for mutations and fail-closed behavior for missing/malformed).
- [x] Step 4.4: Implement `tasks/.../solution/solve.sh` (edits `/app/data` with real commands, no copying from `expected`).
- [x] Step 4.5: Run Oracle and No-Op manually, inspect `jobs/` output layout, and verify `/tests` appeared only during verification.
- [x] Step 4.6: Implement `scripts/check_results.py` to match real Harbor output layout (asserts oracle=1, nop=0, builds summary).
- [x] Step 4.7: Configure `Makefile` with prerequisite-based `check` and plain Windows commands.
- [x] Step 4.8: Run `pytest verifier_selftests/` and `make check` to verify green.
- [x] Step 4.9: docs/LEARNING_NOTES.md Phase 4 summary ("what we built and why"), propose commit, commit, and push.

---

### Phase 5: Agent Runs and Metrics Summary (Budget: 25 min)
**Done when:** Model key is verified via tiny direct call (Step 5.0), 1 trial attempt runs and verifies cost, `no-network` is tested in a live trial, evaluation trial runs and is evaluated, trajectories are scanned for leaked keys, selected sanitized trajectories are copied to `results/trajectories/`, and `scripts/check_results.py` produces `results/RESULTS.md`; committed and pushed.
- [x] Step 5.0: Choose model, test API key and custom headers with a tiny direct script call before using Harbor.
- [x] Step 5.1: Create `.env.example` and set up local `.env` with verified credentials.
- [x] Step 5.2: Configure `Makefile` target `run-agent`.
- [x] Step 5.3: Run 1 trial attempt first, verify token usage and cost.
- [x] Step 5.4: Test `network_mode = "no-network"` with one real trial; document fallback if agent harness needs model access.
- [x] Step 5.5: Run 3 trials via `harbor run ... -k 3` (Skipped per Plan Change Log; single completed trial sample evaluated).
- [x] Step 5.6: Scan saved trajectory files for API keys before staging.
- [x] Step 5.7: Copy selected sanitized trajectories to `results/trajectories/`.
- [x] Step 5.8: Run `scripts/check_results.py` to produce `results/RESULTS.md`.
- [x] Step 5.9: docs/LEARNING_NOTES.md Phase 5 summary ("what we built and why"), propose commit, commit, and push.

---

### Phase 6: Failure Analysis (Budget: 25 to 30 min)
**Done when:** `analysis/FAILURES.md` has our failure taxonomy, user inspects actual agent trajectories, records observations, logs coaching takeaways, and contingency is executed if agent passed all trials; committed and pushed.
- [x] Step 6.1: Initialize `analysis/FAILURES.md` with failure taxonomy.
- [x] Step 6.2: Inspect agent execution trajectories step by step.
- [x] Step 6.3: Coach user through recording observations, categorizing failures, and logging takeaways.
- [x] Step 6.4: Execute contingency if all trials passed (inspect near misses, test weaker model, or add harder trap).
- [x] Step 6.5: docs/LEARNING_NOTES.md Phase 6 summary ("what we built and why"), propose commit, commit, and push.

---

### Phase 7: Polish, README, CI, and Final Push (Budget: 20 min)
**Done when:** `LICENSE` (MIT) and `requirements-ci.txt` are present, CI workflow is green on GitHub, `ruff check` is clean, README has authentic metrics, findings, and Limitations section, user writes 2-minute verbal walkthrough in `LEARNING_NOTES.md`, and final clean commit is pushed.
- [ ] Step 7.1: Add `LICENSE` (MIT).
- [ ] Step 7.2: Create `.github/workflows/ci.yml` (runs lint and verifier self-tests using `requirements-ci.txt`).
- [ ] Step 7.3: Run `ruff check` and fix any formatting or lint issues.
- [ ] Step 7.4: Write comprehensive, authentic `README.md` with real results and Limitations section (one task, single evaluation trial due to free-tier rate limits, one model, first eval project built to learn).
- [ ] Step 7.5: User writes Phase 7 summary and a 2-minute verbal walkthrough of the project in `docs/LEARNING_NOTES.md`.
- [ ] Step 7.6: Confirm `git status` is clean, propose commit message, commit, and push.

---

## 9. Plan Change Log

| Date | Phase / Step | Change Description | Reason and Evidence |
| - | - | - | - |
| Baseline | All | Master Plan established | Initial alignment on tasks, contracts, and constraints |
| 2026-10-12 | Phase 5 / Step 5.5 | Skip 3-attempt run and use single completed trial | Free-tier rate limits make multi-trial runs infeasible; sample stated honestly in README |
| 2026-10-12 | Cross-Phase Consistency | Align codebase with single-run decision across Makefile, scripts, results, and plan docs | Replaced hardcoded 3-attempt assumptions with dynamic sample counting, separated error vs reward-0 trials, and parameterized Makefile |
