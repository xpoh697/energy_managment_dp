import json

path = r'\\192.168.100.5\config\.storage\energy_management_01KKCHQC1H76XNA33EYXJKFB4T'
with open(path, 'r', encoding='utf-8') as f:
    store = json.load(f)

data = store.get("data", {})
overrides = data.get("hourly_manual_overrides", {})
print("HOURLY MANUAL OVERRIDES:")
for k, v in overrides.items():
    print(f"  {k}: {v}")

settings = data.get("settings", {})
print("\nSETTINGS:")
for k, v in settings.items():
    print(f"  {k}: {v}")
