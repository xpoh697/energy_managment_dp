import os
import sys
sys.stdout.reconfigure(encoding='utf-8')

log_path = r"\\192.168.100.5\config\energy_management.log"
if os.path.exists(log_path):
    print("Found energy_management.log on server. Printing last 100 lines...")
    with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()
    
    start = max(0, len(lines) - 100)
    for i in range(start, len(lines)):
        print(f"[{i}] {lines[i].strip()}")
else:
    print("energy_management.log not found on server")
