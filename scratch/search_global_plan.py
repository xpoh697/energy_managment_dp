import sys
sys.stdout.reconfigure(encoding='utf-8')

import os

for root, dirs, files in os.walk("custom_components/energy_management"):
    for file in files:
        if file.endswith(".py") or file.endswith(".js"):
            path = os.path.join(root, file)
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                for i, line in enumerate(f, 1):
                    if "global_plan" in line or "DispatchPlan" in line:
                        print(f"{path}:{i}: {line.strip()}")
