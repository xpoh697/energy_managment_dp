import os
import sys
sys.stdout.reconfigure(encoding='utf-8')

path = os.path.join(r"\\192.168.100.5\config", "energy_management.log.old")
if os.path.exists(path):
    print("Searching old log for TypeError traceback...")
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    
    # Let's find occurrences of "TypeError" and print their context
    start = 0
    while True:
        idx = content.find("TypeError", start)
        if idx == -1:
            break
        print("--- Match ---")
        print(content[max(0, idx - 500) : min(len(content), idx + 1000)])
        start = idx + len("TypeError")
else:
    print("energy_management.log.old not found")
