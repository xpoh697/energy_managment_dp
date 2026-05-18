import os, sys
sys.stdout.reconfigure(encoding='utf-8')

log_path = r'\\192.168.100.5\config\energy_management.log'
if os.path.exists(log_path):
    print("Searching energy_management.log for key words...")
    with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            if any(w in line.lower() for w in ["gatekeeper", "floor", "limit", "block", "surplus", "today"]):
                print(line.strip())
else:
    print("Log not found")
