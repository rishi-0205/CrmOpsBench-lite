# ACME Corporation Employee Offboarding Policy

When an employee departs the organization, the following actions must be taken:

1. **Account Status:** Disable the departed user's account by setting their status to `disabled` in `users.csv`. Do NOT delete the user record, as historical records are required for compliance and auditing.
2. **Group Memberships:** Remove the user from all group memberships in `memberships.csv`. Do NOT delete any groups from `groups.csv`.
3. **Software Licenses:** Release any software license assigned to the user by setting `assigned_to` to an empty value in `licenses.csv`. Do NOT delete license records.
4. **Group Ownership:** If the departed user owns any groups in `groups.csv`, reassign ownership of those groups to the departed user's direct manager (identified by `manager_id` in `users.csv`).
5. **Data Integrity:** Do NOT modify any other users, groups, memberships, or licenses.
