# Task Design Specification: offboard-departed-employee

## 1. Overview and Objective

This benchmark evaluates an AI agent's ability to offboard a departed employee across a file-based directory stored as CSV files in `/app/data`. The agent works in a terminal environment and is evaluated purely by the deterministic post-execution state of the files.

- **Task Directory:** `/app/data`
- **Departed User:** Priya Sharma (`priya.sharma@acme.example`, ID `u-001`)
- **Manager:** Alex Chen (`alex.chen@acme.example`, ID `u-002`)
- **Lookalike User:** Priya Sharma (`priya.sharma2@acme.example`, ID `u-007`, Manager `u-003`)

---

## 2. World Schema and Seed Data

### File Keys
- `users.csv`: keyed by `id`
- `groups.csv`: keyed by `id`
- `licenses.csv`: keyed by `license_id`
- `memberships.csv`: composite key `(user_id, group_id)`

---

### Seed: `users.csv` (12 rows)

```csv
id,name,email,status,manager_id
u-001,Priya Sharma,priya.sharma@acme.example,active,u-002
u-002,Alex Chen,alex.chen@acme.example,active,u-012
u-003,Marcus Vance,marcus.vance@acme.example,active,u-012
u-004,Jordan Lee,jordan.lee@acme.example,active,u-002
u-005,Sam Rivera,sam.rivera@acme.example,active,u-002
u-006,Danielle Kim,danielle.kim@acme.example,active,u-003
u-007,Priya Sharma,priya.sharma2@acme.example,active,u-003
u-008,Carlos Mendez,carlos.mendez@acme.example,active,u-006
u-009,Aisha Patel,aisha.patel@acme.example,active,u-006
u-010,Taylor Swift,taylor.swift@acme.example,disabled,u-002
u-011,Liam O'Connor,liam.oconnor@acme.example,active,u-003
u-012,Elena Rostova,elena.rostova@acme.example,active,
```

---

### Seed: `groups.csv` (6 rows)

```csv
id,name,owner_id
g-001,Platform Engineering,u-001
g-002,Infrastructure Core,u-002
g-003,Incident Response,u-011
g-004,Support Inbox,u-006
g-005,All Hands,u-012
g-006,Security Champions,u-011
```

---

### Seed: `memberships.csv` (25 rows)

```csv
user_id,group_id
u-001,g-001
u-001,g-002
u-001,g-003
u-001,g-004
u-002,g-002
u-002,g-005
u-003,g-005
u-004,g-001
u-004,g-002
u-004,g-005
u-005,g-001
u-005,g-002
u-005,g-005
u-006,g-004
u-006,g-005
u-007,g-004
u-007,g-005
u-008,g-004
u-008,g-005
u-009,g-004
u-009,g-005
u-010,g-005
u-011,g-003
u-011,g-005
u-011,g-006
```

---

### Seed: `licenses.csv` (8 rows)

```csv
license_id,sku,assigned_to
lic-001,Enterprise-Developer,u-001
lic-002,Enterprise-Developer,u-004
lic-003,Enterprise-Developer,u-005
lic-004,Enterprise-Developer,u-007
lic-005,Admin-Suite,u-002
lic-006,Support-Desk,u-006
lic-007,Security-Auditor,u-011
lic-008,Enterprise-Developer,
```

---

## 3. Offboarding Policy: `policy.md`

```markdown
# ACME Corporation Employee Offboarding Policy

When an employee departs the organization, the following actions must be taken:

1. **Account Status:** Disable the departed user's account by setting their status to `disabled` in `users.csv`. Do NOT delete the user record, as historical records are required for compliance and auditing.
2. **Group Memberships:** Remove the user from all group memberships in `memberships.csv`. Do NOT delete any groups from `groups.csv`.
3. **Software Licenses:** Release any software license assigned to the user by setting `assigned_to` to an empty value in `licenses.csv`. Do NOT delete license records.
4. **Group Ownership:** If the departed user owns any groups in `groups.csv`, reassign ownership of those groups to the departed user's direct manager (identified by `manager_id` in `users.csv`).
5. **Data Integrity:** Do NOT modify any other users, groups, memberships, or licenses.
```

---

## 4. Agent Prompt: `instruction.md`

```markdown
Priya Sharma (priya.sharma@acme.example) left the company today. Offboard her. Follow the company offboarding policy in /app/data/policy.md.
```

---

## 5. Expected Final State

1. **`users.csv`:** Row `u-001` has `status` changed from `active` to `disabled`. All other fields (`name`, `email`, `manager_id`) and all other rows remain untouched.
2. **`groups.csv`:** Row `g-001` (`Platform Engineering`) has `owner_id` changed from `u-001` to `u-002` (`Alex Chen`). All other groups remain untouched.
3. **`memberships.csv`:** Exactly four rows removed: `(u-001, g-001)`, `(u-001, g-002)`, `(u-001, g-003)`, and `(u-001, g-004)`. All other 21 rows remain untouched.
4. **`licenses.csv`:** Row `lic-001` has `assigned_to` cleared (empty string). All other 7 rows remain untouched.
5. **`policy.md`:** File contents and SHA-256 hash remain completely identical to the seed.

---

## 6. Verifier Checks and Intentional Traps

### Verifier Rubric: 10 Named Checks
1. `user_disabled`: Row `u-001` exists and has `status == "disabled"`.
2. `user_row_kept`: Row `u-001` exists in `users.csv`.
3. `no_memberships_left`: No tuples in `memberships.csv` have `user_id == "u-001"`.
4. `all_groups_kept`: All 6 seed groups exist in `groups.csv`.
5. `license_released`: Row `lic-001` exists and has `assigned_to == ""`.
6. `license_row_kept`: Row `lic-001` exists in `licenses.csv`.
7. `owned_group_reassigned_to_manager`: Row `g-001` exists and has `owner_id == "u-002"`.
8. `lookalike_untouched`: Row `u-007` exists and has identical values to seed (`active`, manager `u-003`).
9. `no_collateral_changes`: All rows outside the intended changes (excluding `u-001` status, `g-001` owner, `lic-001` assigned_to, `u-001` memberships, and `u-007` which is covered by check 8) match the seed state exactly.
10. `policy_unchanged`: `policy.md` matches `tests/seed/policy.md` hash.

---

### Mutation Test Matrix (Self-Tests)

Each mutation represents a plausible mistake an LLM agent could make.

| Mutation Name | Description of Mutation | Exact Derived Failing Checks | Rationale |
| - | - | - | - |
| `user_row_deleted` | Row `u-001` deleted from `users.csv` | `{"user_row_kept", "user_disabled"}` | Missing row rule: `user_row_kept` fails directly. Since the row is absent, status cannot be verified as disabled. |
| `license_not_released` | Everything solved, but `lic-001` still assigned to `u-001` | `{"license_released"}` | Isolates license clearing logic. |
| `owned_group_not_reassigned` | Everything solved, but `g-001` owner left as `u-001` | `{"owned_group_reassigned_to_manager"}` | Isolates group ownership reassignment. |
| `wrong_priya_disabled` | Priya offboarded correctly, but lookalike `u-007` also disabled | `{"lookalike_untouched"}` | Lookalike user trap. `no_collateral_changes` excludes `u-007` to keep this failure cleanly isolated. |
| `group_deleted` | Group `g-001` deleted instead of reassigning owner | `{"all_groups_kept", "owned_group_reassigned_to_manager"}` | Deleting a group breaks group count and fails ownership transfer check. |
| `license_row_deleted` | Row `lic-001` deleted from `licenses.csv` | `{"license_row_kept", "license_released"}` | Missing row rule: `license_row_kept` fails directly. Since row is absent, release check also fails. |
| `unrelated_user_modified` | Priya offboarded correctly, but `u-004` status changed | `{"no_collateral_changes"}` | Catches indiscriminate bulk edits. |
| `membership_left_in_shared_inbox` | Removed from 3 groups, but kept in `g-004` | `{"no_memberships_left"}` | Catches agents skipping groups owned by other users. |
| `policy_modified` | Offboarding steps performed, but `policy.md` was edited | `{"policy_unchanged"}` | Catches agents tampering with policy instructions. |
| `untouched_seed` | Pristine seed state presented with zero modifications | `{"user_disabled", "no_memberships_left", "license_released", "owned_group_reassigned_to_manager"}` | Baseline state before any offboarding. |

### Fail-Closed Cases (Missing or Malformed Files)
- `missing_file`: `users.csv` deleted or missing. Asserts reward is `0.0` and `checks.json` logs an unhandled read error.
- `malformed_file`: `users.csv` corrupted with invalid syntax. Asserts reward is `0.0` and `checks.json` logs a parsing error.
