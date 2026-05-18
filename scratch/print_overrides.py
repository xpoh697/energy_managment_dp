import json
import os
import sys
sys.stdout.reconfigure(encoding='utf-8')

path = r"\\192.168.100.5\config\.storage\energy_management_01KKCHQC1H76XNA33EYXJKFB4T"
if os.path.exists(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    store_data = data.get("data", {})
    print("hourly_manual_overrides:", store_data.get("hourly_manual_overrides"))
    print("manual_mode_overrides:", store_data.get("manual_mode_overrides"))
