# Failure Analysis and Evaluation Taxonomy

This document outlines the failure taxonomy for `offboarding-bench`, audits the recorded agent trajectories, and details key evaluation engineering takeaways.

---

## 1. Evaluation Methodology and Sample Overview

The evaluation benchmark tested AI agents on the `offboard-departed-employee` task using Harbor and Docker sandboxing under strict network isolation (`network_mode = "no-network"`).

- **Evaluated Models:**
  - `gemini/gemini-flash-latest` (Google AI Studio)
  - `groq/qwen/qwen3.8-27b` (Groq on-demand tier)
  - `groq/openai/gpt-oss-120b` and `groq/openai/gpt-oss-20b` (Groq on-demand tier)
- **Sample Summary:**
  - Total trials attempted: 11
  - Passing trials: 3 (Oracle reference solution, Hello-World baseline, and Gemini Flash agent rollout)
  - Failing trials: 1 (No-op baseline scoring 0.0)
  - Errored trials: 7 (Rate limit cutoffs and cancelled attempts due to provider free-tier ceilings)

---

## 2. Hierarchical Failure Taxonomy

We categorize potential benchmark failures into two distinct tiers: Task Behavioral Failures (errors in agent problem-solving) and Infrastructure / Operational Failures (errors in the evaluation environment or provider connectivity).

### Category A: Task Behavioral Failures (BEH)

| Code | Failure Mode | Trigger / Description | Targeted Verifier Check |
| --- | --- | --- | --- |
| `BEH-01` | **Lookalike Identity Confusion** | Modifying or disabling the active coworker sharing the same name (`u-007`, Priya Sharma 2) instead of or in addition to the departed employee (`u-001`). | `lookalike_untouched`, `wrong_priya_disabled` |
| `BEH-02` | **Audit Trail Destruction** | Deleting the user row or license row rather than updating status or clearing assignments, violating compliance retention rules. | `user_row_kept`, `license_row_kept` |
| `BEH-03` | **Incomplete Offboarding** | Leaving dangling memberships, failing to clear license assignments, or failing to reassign owned groups to direct managers. | `no_memberships_left`, `license_released`, `owned_group_reassigned_to_manager` |
| `BEH-04` | **Collateral Damage** | Deleting intact groups, modifying unrelated employee rows, or corrupting/editing the policy document itself. | `all_groups_kept`, `no_collateral_changes`, `policy_unchanged` |

### Category B: Infrastructure and Operational Failures (OPS)

| Code | Failure Mode | Trigger / Description | Impact |
| --- | --- | --- | --- |
| `OPS-01` | **Sliding-Window Token Exhaustion** | Multi-turn agent rollouts accumulate conversational history. Provider limits (e.g., 7,000 ITPM or 1,000 OTPM on Groq) reject valid requests mid-run. | `RateLimitError` aborts trial before grading |
| `OPS-02` | **Tool Protocol Incompatibility** | Model fine-tuned exclusively for JSON tool-calling emits OpenAI syntax (`{"name": "container.exec"}`) when prompted for raw terminal commands. | HTTP 400 `tool_use_failed` |
| `OPS-03` | **Missing Host Tools** | Agent attempts to invoke diagnostic utilities not bundled in minimal container base images (e.g. `file` in `python:3.12-slim`). | Non-zero exit code in agent shell |

---

## 3. Trajectory Inspection: The Passing Trial

- **File:** `results/trajectories/gemini_flash_pass_trial.json`
- **Agent:** `terminus-2`
- **Model:** `gemini/gemini-flash-latest`
- **Outcome:** **PASS** (Reward 1.0, 10/10 checks passed)
- **Total Tokens:** 33,474 | **Cost:** $0.035 USD | **Runtime:** 2m 11s

### Step-by-Step Rollout Analysis

1. **Step 2 (Inspection):** The agent read `/app/data/policy.md` and listed the directory. It correctly extracted all 5 policy constraints before touching any data.
2. **Step 3 (Schema Discovery):** Ran `head -n 50 /app/data/*.csv`. Discovered user `u-001` and discovered lookalike `u-007`.
3. **Step 4 (Trap Avoidance & Near Miss):**
   - *Trap Avoidance:* The agent explicitly noted in its internal reasoning:
     > `"u-001: Priya Sharma (priya.sharma@acme.example), manager_id: u-002. Note that u-007 is priya.sharma2@acme.example and should NOT be touched."`
   - *Near Miss:* The agent executed `git status 2>/dev/null || true; file /app/data/*.csv`. The `file` utility was missing in `python:3.12-slim-bookworm` (`bash: file: command not found`). Rather than hallucinating or aborting, the agent gracefully recovered.
4. **Step 5 (Line Ending Verification):** Checked line endings programmatically using Python binary mode:
   ```python
   with open("/app/data/users.csv", "rb") as f:
       print(repr(f.readline()))
   ```
   Confirmed `\n` line endings to avoid introducing Windows CRLF characters.
5. **Step 6 (Atomic Update Script):** Authored an inline Python script using standard `csv.DictReader` and `csv.DictWriter(lineterminator='\n')`:
   - Included defensive assertions: `assert user_id == 'u-001'` and `assert manager_id == 'u-002'`.
   - Updated `users.csv` status to `disabled` without deleting the row.
   - Filtered `memberships.csv` to remove `u-001` records.
   - Released `assigned_to` in `licenses.csv`.
   - Reassigned `groups.csv` ownership to `u-002`.
6. **Step 7 & 8 (Pre-Completion Verification):** Dumped all CSV files, audited every diff against the 5 policy rules, and confirmed completion.

---

## 4. Trajectory Inspection: The Rate-Limited Trial

- **File:** `results/trajectories/groq_qwen_ratelimit_trial.json`
- **Agent:** `terminus-2`
- **Model:** `groq/qwen/qwen3.8-27b`
- **Outcome:** **ERROR** (`RateLimitError` on Turn 6)
- **Tokens Used Prior to Error:** 15,055 prompt tokens, 2,065 completion tokens

### Step-by-Step Rollout Analysis

1. **Steps 2 to 4:** The model read `policy.md` and inspected `users.csv`, `memberships.csv`, `licenses.csv`, and `groups.csv`.
2. **Step 5 (Task Execution):** The model correctly wrote the offboarding script, preserving lookalike `u-007`, updating status to `disabled`, removing memberships, releasing licenses, and reassigning group ownership.
3. **Step 6 (Completion Attempt):** The model audited the files and called `mark_task_complete`.
4. **The Failure Point:** Harbor requires a two-step completion handshake (`Are you sure? Repeat task_complete: true`). LiteLLM submitted Turn 6 with conversational history totaling 5,972 input tokens.
5. **Root Cause:** Groq's on-demand tier enforces a 7,000 Input Tokens Per Minute (ITPM) limit. Because the previous turn had consumed 4,168 tokens in the same 60-second window, 4,168 + 5,972 = 10,140 > 7,000 ITPM. Groq returned HTTP 429:
   > `"Rate limit reached for model qwen/qwen3.8-27b on input tokens per minute (ITPM): Limit 7000, Used 4168, Requested 5972. Please try again in 26.9s."`
6. **Classification:** This is an operational error (`OPS-01`), not an agent reasoning error. The agent solved the task correctly in state, but the trial errored out before the verifier executed.

---

## 5. Evaluation Engineering Takeaways

1. **State-Based Grading Prevents False Attribution:**
   Inspecting filesystem state directly proves that both Gemini Flash and Qwen solved the underlying problem. Relying on conversational output or unhandled exception codes alone would misdiagnose Qwen as a capability failure.
2. **Deterministic Traps Reveal Real Capabilities:**
   Both models actively recognized the lookalike user trap (`u-007`) and avoided modifying it. This validates that the benchmark presents an authentic discrimination challenge rather than a trivial name-matching task.
3. **Air-Gapped Isolation Works:**
   Under `network_mode = "no-network"`, the agent cannot leak customer data or fetch external dependencies. It relies entirely on Python and standard shell utilities pre-installed in the container.
4. **Harness Decoupling:**
   When designing multi-turn agent benchmarks, the harness should provide turn-level throttling or local proxy caching to insulate evaluations from cloud provider rate limits.
