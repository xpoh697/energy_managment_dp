import json

path = r'\\192.168.100.5\config\.storage\energy_management_01KKCHQC1H76XNA33EYXJKFB4T'
with open(path, 'r', encoding='utf-8') as f:
    store = json.load(f)

data = store.get("data", {})
debug_info = data.get("calculation_debug", {})
print("CALCULATION DEBUG INFO:")
for k, v in debug_info.items():
    print(f"  {k}: {v}")
