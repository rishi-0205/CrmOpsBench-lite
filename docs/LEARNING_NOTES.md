# Learning Notes and Interview Preparation

This document records key terminology, architectural decisions, and conceptual takeaways after each phase. It serves as personal preparation for evaluation engineering interviews.

---

## Phase 0: Environment Setup and Baseline

### Glossary
- **Virtual Environment (`.venv`):** An isolated Python directory that prevents package version conflicts between projects and system tools.
- **Line Endings (`.gitattributes`):** Configuration forcing LF (`\n`) endings across the repository so Linux containers never fail on Windows CRLF (`\r\n`) characters.
- **Oracle Agent:** A built-in Harbor agent that runs the task's known reference solution (`solve.sh`) to prove the environment, instructions, and verifier work end to end.
- **State-Based Grading:** Evaluating an AI agent purely by inspecting the final filesystem modifications inside the sandbox, rather than evaluating conversational text output.

### What We Built and Why
We established our project baseline on Windows 11 using PowerShell and Docker Desktop with the WSL2 Linux engine. We created an isolated Python 3.13 virtual environment, pinned Harbor 0.24.0, pytest, and ruff, and verified that Harbor can launch containers, execute tasks, and score rewards cleanly on Windows. Finally, we inspected Harbor's official task boilerplate to confirm the directory layout before authoring custom task files.

---

## Phase 1: Task Design and Specification

### Glossary
- **Mutation Testing (in Evals):** Generating deliberately broken world states to verify that our grading suite catches every specific failure mode.
- **Fail-Closed Verification:** Ensuring any missing entity, corrupted syntax, or unhandled exception deterministically grades as a failure (reward 0).
- **Orthogonal Checks:** Structuring verification rules so distinct errors (e.g., lookalike user modifications vs. collateral edits) trigger separate, isolated checks.

### What We Built and Why
We wrote `docs/DESIGN.md` defining our exact 12-user, 6-group, 25-membership, and 8-license seed dataset. We formalized the 5-rule policy, the agent prompt, and the 10-check verifier rubric. Crucially, we reasoned through each failure trap to derive the exact set of failing check names before writing any verifier code.

---

## Phase 2: Environment and World Setup

### Glossary
- **Principle of Least Privilege (in Evals):** Running the agent as an unprivileged OS user (`agent`, UID 1000) so it cannot tamper with system-level files or escape task boundaries.
- **Runtime Test Injection:** Harbor's security pattern of keeping `tests/` and `solution/` out of the Docker image during the agent phase, injecting `tests/` only when verification begins.

### What We Built and Why
We implemented the task sandbox inside `tasks/offboard-departed-employee/`. We wrote the seed CSV files and policy in `environment/data/`, created the agent prompt in `instruction.md`, and authored a non-root `Dockerfile` based on `python:3.12-slim-bookworm`. Finally, we proved via `docker run` that the container runs as `agent` and that neither `/tests` nor `/solution` exist in the image while the agent works.

---

## Phase 3: Tooling and Verifier Implementation

### Glossary
- **Deterministic State Verifier:** A programmatic evaluation script that inspects filesystem records directly against ground truth, avoiding stochastic LLM judges.
- **Pure Verification Functions:** Self-contained check functions that take directory paths as explicit parameters and return booleans without side effects, enabling rapid host-side testing.

### What We Built and Why
We built `pyproject.toml` to configure `ruff` and link `pytest` to `tasks/.../tests`. We established immutable reference baselines in `tests/seed/` and `tests/expected/`. Finally, we authored `checks.py` containing 10 pure verification checks and a fail-closed `main()` entrypoint executed by `test.sh`. This produces `/logs/verifier/reward.txt` and diagnostic report `/logs/verifier/checks.json`.

---

## Phase 4: Proof, Self-Tests, Oracle, and No-Op

### Glossary
- **Explainable Verification vs. Scalar Reward:** A scalar reward (0.0 or 1.0) provides a summary metric for benchmark pass rates, whereas structured diagnostic logs (`checks.json`) isolate the exact step and broken invariant, enabling granular failure analysis.
- **`.PHONY` Target in Make:** Declares that a target represents a named action rather than a disk file, ensuring Make always runs the commands even if a file or directory with that name exists.

### What We Built and Why
We proved the verifier is robust and the task is solvable before running any AI agent. We implemented host-side test suites in `verifier_selftests/` verifying seed integrity byte-for-byte, verifying programmatic oracle transformations against ground truth, and testing all 10 failure mutations against their exact derived check sets (along with fail-closed missing/malformed file handling). We authored the reference solution `solve.sh` and ran live Harbor trials inside Docker, confirming the oracle scored 1.0 and the no-op scored 0.0. Finally, we created `scripts/check_results.py` and `Makefile` to dynamically audit job outputs and automate baseline assertions.

---

## Phase 5: Agent Runs and Metrics Summary

### Glossary
- **Pre-Flight Model Smoke Testing:** Testing API credentials and model endpoints with a small standalone script before invoking benchmark frameworks to isolate external API and alias errors from benchmark evaluation code.
- **Air-Gapped Sandbox (`no-network`):** Disabling network access inside the execution container during agent rollouts to prevent customer data exfiltration and external script downloads, ensuring evaluation measures pure local tool proficiency.
- **Output Tokens Per Minute (OTPM) Bottlenecks:** Provider rate limits that throttle rapid multi-turn agent conversations within a 60-second sliding window, requiring turn-level retry handling or honest reporting of sample sizes.

### What We Built and Why
We established model credential templates in `.env.example` and pre-flight connectivity verification in `scripts/test_model_call.py`. We enforced network isolation inside the container with `network_mode = "no-network"` in `task.toml`. We executed live agent evaluations using Harbor's `terminus-2` agent. The agent scored a full 1.0 reward (passing all 10 checks) in an air-gapped run using Gemini Flash. When testing open models on Groq, we identified provider-level token-per-minute limits and configured native Harbor job retries. We documented the single completed trial sample honestly in the Plan Change Log, scanned all saved trajectories for leaked API keys using `scripts/scan_trajectories.py`, archived sanitized trajectories in `results/trajectories/`, and generated our evaluation summary in `results/RESULTS.md` using `scripts/check_results.py`.

---

## Phase 6: Failure Analysis

### Glossary
- **Failure Taxonomy:** A standardized classification schema that groups evaluation failures by root cause (e.g. behavioral task errors vs. operational infrastructure errors) rather than simple scalar pass/fail scores.
- **Near-Miss Auditing:** Reviewing passing trajectories for suboptimal commands, missing tool failures, or risky patterns that could cause failures under different environment conditions.

### What We Built and Why
We created `analysis/FAILURES.md` to classify benchmark failure modes and analyze recorded agent trajectories. We audited the passing trial (`gemini_flash_pass_trial.json`), verifying that the agent deliberately avoided the lookalike user trap, preserved audit history, checked newline line endings via binary file inspection, and gracefully recovered when the `file` utility was missing in Debian slim. We also audited the rate-limited trial (`groq_qwen_ratelimit_trial.json`), proving that the agent implemented the correct state mutations, but crashed during the final handshake because accumulated multi-turn prompt tokens exceeded Groq's 7,000 ITPM rate limit. This confirmed the value of state-based grading over conversational parsing.

---

## Phase 7: Polish, README, and Final Push

### Key Concepts Added
- **State-Based Benchmark Soundness:** Ensuring that benchmark evaluations do not depend on conversational output or agent claims, but solely on deterministic verifications of post-run disk state.
- **Reproducibility Contract:** Providing exact, tested shell commands alongside Makefile targets so researchers can reproduce baselines and agent runs on any platform.
- **Fail-Closed Verification:** Graders that strictly fail with reward 0.0 if any required resource is missing, unreadable, or malformed, preventing accidental passes.

### What We Built and Why
We finalized `offboarding-bench` as a complete, transparent evaluation portfolio piece. We added an MIT `LICENSE`, cleaned all linting errors via `ruff check`, and authored a comprehensive `README.md`. The README presents honest sample metrics (1 attempt, 1 model, 1 task) due to provider free-tier rate limits, documents the exact trajectory commands executed by Gemini Flash, and specifies both verified and unverified isolation boundaries. We also established a dual-track "How to run" guide supporting PowerShell and macOS/Linux with verified Makefile targets.

### 2-Minute Verbal Walkthrough

> "This project is `offboarding-bench`, a deterministic evaluation benchmark for AI coding and operations agents.
>
> The problem it tests is enterprise offboarding. When an employee departs, an agent must update four relational CSV files in a sandboxed container: disable the user account without deleting the record, remove all group memberships, clear software licenses, and reassign owned groups to their direct manager. The environment includes intentional traps, including an active coworker who shares the exact same name, strict compliance rules requiring historical record retention, and air-gapped network isolation.
>
> What makes this benchmark robust is how grading works. Rather than evaluating LLM output with another LLM or parsing conversational chat, grading is purely state-based. A Python verifier runs inside the container and tests the filesystem against 10 explicit checks. To prove the verifier itself is sound, we wrote 16 automated self-tests across 10 mutation scenarios, confirming that specific agent errors produce exact derived sets of failing checks, and validated reference oracle (1.0) and no-op (0.0) baselines.
>
> When we ran `gemini/gemini-flash-latest` via the Harbor framework, the agent scored a perfect 1.0 in 2 minutes and 11 seconds. The trajectory showed interesting behavior: the agent deliberately avoided the lookalike user, used binary file reads to preserve Unix line endings, authored defensive Python assertions, and gracefully recovered when a diagnostic shell tool was missing from the container. We also observed provider rate limits on multi-turn rollouts, reinforcing why benchmarking harnesses must account for token accumulation during evaluation."

