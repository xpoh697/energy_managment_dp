import os
import sys
sys.stdout.reconfigure(encoding='utf-8')

for f_name in ["energy_management.log", "energy_management.log.old"]:
    path = os.path.join(r"\\192.168.100.5\config", f_name)
    if os.path.exists(path):
        print(f"Searching {f_name}...")
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
        count = 0
        for line in reversed(lines):
            if "extra_state_attributes" in line or "iterable" in line or "TypeError" in line:
                print(line.strip())
                count += 1
                if count > 10:
                    break
    else:
        print(f"{f_name} not found")
