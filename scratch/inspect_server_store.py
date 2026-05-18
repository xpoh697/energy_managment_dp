import json
import os
import sys
sys.stdout.reconfigure(encoding='utf-8')

path = r"\\192.168.100.5\config\.storage\energy_management_01KKCHQC1H76XNA33EYXJKFB4T"
if os.path.exists(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    print("Store keys:")
    store_data = data.get("data", {})
    for k, v in store_data.items():
        if isinstance(v, dict):
            print(f"  {k} (dict, size: {len(v)})")
        elif isinstance(v, list):
            print(f"  {k} (list, size: {len(v)})")
        else:
            print(f"  {k}: {v} (type: {type(v).__name__})")
else:
    print("Store file not found")
