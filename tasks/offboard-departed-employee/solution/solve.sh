#!/bin/bash
set -euo pipefail

# Solve script for offboard-departed-employee task
# Performs in-place edits on /app/data conforming to offboarding policy.

python3 - <<'EOF'
import csv
from pathlib import Path

data_dir = Path("/app/data")

# 1. Update users.csv: disable departed employee Priya Sharma (u-001)
users_file = data_dir / "users.csv"
with users_file.open("r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    fieldnames = reader.fieldnames
    rows = list(reader)

for row in rows:
    if row["id"] == "u-001":
        row["status"] = "disabled"

with users_file.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

# 2. Update groups.csv: reassign ownership of g-001 to manager u-002
groups_file = data_dir / "groups.csv"
with groups_file.open("r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    fieldnames = reader.fieldnames
    rows = list(reader)

for row in rows:
    if row["id"] == "g-001":
        row["owner_id"] = "u-002"

with groups_file.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

# 3. Update licenses.csv: revoke assigned license from u-001
licenses_file = data_dir / "licenses.csv"
with licenses_file.open("r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    fieldnames = reader.fieldnames
    rows = list(reader)

for row in rows:
    if row["license_id"] == "lic-001":
        row["assigned_to"] = ""

with licenses_file.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

# 4. Update memberships.csv: remove all group memberships for u-001
memberships_file = data_dir / "memberships.csv"
with memberships_file.open("r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    fieldnames = reader.fieldnames
    rows = list(reader)

remaining_memberships = [row for row in rows if row["user_id"] != "u-001"]

with memberships_file.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(remaining_memberships)

print("Offboarding actions applied successfully.")
EOF
