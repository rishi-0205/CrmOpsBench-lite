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
