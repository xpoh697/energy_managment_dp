import os
import sys
sys.stdout.reconfigure(encoding='utf-8')

log_path = r"\\192.168.100.5\config\energy_management.log"
if os.path.exists(log_path):
    print("Found energy_management.log on server. Searching...")
    with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()
    
    # Search for the error
    found = False
    for i, line in enumerate(lines):
        if "iterable" in line or "TypeError" in line or "container" in line:
            print(f"Line {i}: {line.strip()}")
            # Print context lines around it
            start = max(0, i - 10)
            end = min(len(lines), i + 5)
            print("--- Context ---")
            for j in range(start, end):
                print(f"  [{j}] {lines[j].strip()}")
            print("---------------\n")
            found = True
    if not found:
        print("No matches found in energy_management.log")
else:
    print("energy_management.log not found on server")
