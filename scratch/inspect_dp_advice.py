import os
import re

log_path = r"\\192.168.100.5\config\energy_management.log"
if os.path.exists(log_path):
    with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()
    print("Searching logs for DP Optimizer / advice...")
    found = 0
    for line in reversed(lines):
        if "DP Optimizer" in line or "dp_advice" in line or "plan_by_timestamp" in line or "adv:" in line:
            print(line.strip())
            found += 1
            if found > 20:
                break
else:
    print("Log file not found")
