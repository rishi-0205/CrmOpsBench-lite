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
