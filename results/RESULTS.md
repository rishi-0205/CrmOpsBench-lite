# Evaluation Results Summary

- **Total Sample Size:** 13 trial(s) across 13 job(s)
- **Outcome Counts:** 4/13 passed, 2/13 failed (reward 0.0), 7/13 errored

> Note: For small evaluation samples, results are reported as exact counts rather than percentage estimates.

| Job / Timestamp | Agent | Model | Trial Name | Reward | Status | Details |
| --- | --- | --- | --- | --- | --- | --- |
| `2026-10-11__00-37-07` | `oracle` | `unknown` | `hello-world__v9Z3UEu` | `1.0` | **PASS** | Reward 1.0 |
| `2026-10-11__17-37-36` | `oracle` | `unknown` | `offboard-departed-employee__3SvNn8a` | `1.0` | **PASS** | 10/10 checks passed |
| `2026-10-11__17-39-52` | `nop` | `unknown` | `offboard-departed-employee__RckXbcf` | `0.0` | **FAIL (Reward 0.0)** | 6/10 checks passed |
| `2026-10-11__22-38-39` | `terminus-2` | `gemini/gemini-flash-latest` | `offboard-departed-employee__z4Aao8w` | `1.0` | **PASS** | 10/10 checks passed |
| `2026-10-11__22-51-22` | `terminus-2` | `gemini/gemini-flash-latest` | `offboard-departed-employee__rvfsSn2` | `0.0` | **ERROR (RateLimitError)** | Trial hit an unhandled exception or rate limit |
| `2026-10-11__22-57-39` | `terminus-2` | `gemini/gemini-flash-latest` | `offboard-departed-employee__8KSjR72` | `0.0` | **ERROR (RateLimitError)** | Trial hit an unhandled exception or rate limit |
| `2026-10-11__23-16-25` | `terminus-2` | `groq/openai/gpt-oss-120b` | `offboard-departed-employee__j43DgbA` | `0.0` | **ERROR (RateLimitError)** | Trial hit an unhandled exception or rate limit |
| `2026-10-12__00-02-20` | `terminus-2` | `groq/openai/gpt-oss-20b` | `offboard-departed-employee__aukcWwv` | `0.0` | **ERROR (CancelledError)** | Trial hit an unhandled exception or rate limit |
| `2026-10-12__00-31-53` | `terminus-2` | `groq/qwen/qwen3.8-27b` | `offboard-departed-employee__kPVjWzo` | `0.0` | **ERROR (RateLimitError)** | Trial hit an unhandled exception or rate limit |
| `2026-10-12__01-06-56` | `terminus-2` | `groq/qwen/qwen3.8-27b` | `offboard-departed-employee__SkCCMPc` | `0.0` | **ERROR (CancelledError)** | Trial hit an unhandled exception or rate limit |
| `2026-10-12__16-56-14` | `terminus-2` | `groq/qwen/qwen3.8-27b` | `offboard-departed-employee__VNf96dV` | `0.0` | **ERROR (RateLimitError)** | Trial hit an unhandled exception or rate limit |
| `2026-10-12__17-31-39` | `nop` | `unknown` | `offboard-departed-employee__5v24yUt` | `0.0` | **FAIL (Reward 0.0)** | 6/10 checks passed |
| `2026-10-12__17-32-14` | `oracle` | `unknown` | `offboard-departed-employee__CDMUgEF` | `1.0` | **PASS** | 10/10 checks passed |
