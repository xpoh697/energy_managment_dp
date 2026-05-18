import json
import os
import sys
sys.stdout.reconfigure(encoding='utf-8')

path = r"\\192.168.100.5\config\.storage\core.config_entries"
if os.path.exists(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    for entry in data.get("data", {}).get("entries", []):
        if entry.get("domain") == "energy_management":
            print("Entry ID:", entry.get("entry_id"))
            print("Data keys:")
            for k, v in entry.get("data", {}).items():
                print(f"  {k}: {repr(v)} (type: {type(v).__name__})")
            print("Options keys:")
            for k, v in entry.get("options", {}).items():
                print(f"  {k}: {repr(v)} (type: {type(v).__name__})")
else:
    print("core.config_entries not found")
