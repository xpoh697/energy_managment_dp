import json
import os

with open(r'\\192.168.100.5\config\.storage\energy_management_01KKCHQC1H76XNA33EYXJKFB4T', 'r', encoding='utf-8') as f:
    store = json.load(f)

data = store.get("data", {})
sensor_last_values = data.get("sensor_last_values", {})

print("ALL ENTITY KEYS CONTAINING 'energy' or 'management':")
for k in sorted(sensor_last_values.keys()):
    if "energy" in k or "management" in k:
        print(f"  {k}")
