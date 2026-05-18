import sys
import json
sys.stdout.reconfigure(encoding='utf-8')

with open(r'\\192.168.100.5\config\.storage\energy_management_01KKCHQC1H76XNA33EYXJKFB4T', 'r', encoding='utf-8') as f:
    store = json.load(f)

store_data = store.get("data", {})
settings = store_data.get("settings", {})
print("SETTINGS:")
for k, v in settings.items():
    print(f"{k}: {v}")
