import json

with open(r'\\192.168.100.5\config\.storage\energy_management_01KKCHQC1H76XNA33EYXJKFB4T', 'r', encoding='utf-8') as f:
    store = json.load(f)

data = store.get("data", {})
print("Top-level keys in data:", list(data.keys()))

settings = data.get("settings", {})
print("Settings:")
for k, v in settings.items():
    print(f"  {k}: {v}")

print("\nHourly Manual Overrides:")
overrides = data.get("hourly_manual_overrides", {})
for k, v in overrides.items():
    print(f"  {k}: {v}")
