import json, sys
sys.stdout.reconfigure(encoding='utf-8')

with open(r'\\192.168.100.5\config\.storage\core.config_entries', 'r', encoding='utf-8') as f:
    entries = json.load(f)

for item in entries.get("data", {}).get("entries", []):
    if item.get("domain") == "energy_management":
        print("ENERGY MANAGEMENT CONFIG ENTRY:")
        print(json.dumps(item.get("options", item.get("data", {})), indent=2, ensure_ascii=False))
