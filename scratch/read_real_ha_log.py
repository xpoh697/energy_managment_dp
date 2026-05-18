import os
import sys
sys.stdout.reconfigure(encoding='utf-8')

path = r"\\192.168.100.5\config\home-assistant.log"
print(f"Checking if {path} exists...")
if os.path.exists(path):
    print("Found home-assistant.log! Reading latest lines...")
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()
    
    # Search for latest 30 lines containing InverterOperationModeSensor or TypeError
    count = 0
    for i in range(len(lines) - 1, -1, -1):
        line = lines[i]
        if "InverterOperationModeSensor" in line or "extra_state_attributes" in line or "TypeError" in line:
            print(f"Line {i}: {line.strip()}")
            # Print context lines around it
            start = max(0, i - 10)
            end = min(len(lines), i + 5)
            print("--- Context ---")
            for j in range(start, end):
                print(f"  [{j}] {lines[j].strip()}")
            print("---------------\n")
            count += 1
            if count >= 5:
                break
else:
    print("home-assistant.log not found!")
