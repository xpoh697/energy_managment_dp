import json

with open(r'\\192.168.100.5\config\.storage\energy_management_01KKCHQC1H76XNA33EYXJKFB4T', 'r', encoding='utf-8') as f:
    store = json.load(f)

data = store.get("data", {})
settings = data.get("settings", {})
last_vals = data.get("sensor_last_values", {})

print("SETTINGS:")
for k, v in settings.items():
    print(f"  {k}: {v}")

print("\nSENSOR LAST VALUES:")
for k, v in last_vals.items():
    if "forecast" in k or "battery" in k or "inverter" in k or "soc" in k or "price" in k:
        print(f"  {k}: {v}")
