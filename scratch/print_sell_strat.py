import json

path = r'\\192.168.100.5\config\.storage\energy_management_01KKCHQC1H76XNA33EYXJKFB4T'
with open(path, 'r', encoding='utf-8') as f:
    store = json.load(f)

data = store.get("data", {})
# Let's see what is inside sensor_last_values or settings to find how it calculates strategies
print("SETTINGS:")
for k, v in data.get("settings", {}).items():
    if "sell" in k or "soc" in k or "discharge" in k:
        print(f"  {k}: {v}")
