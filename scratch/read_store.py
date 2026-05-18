import json

with open(r'\\192.168.100.5\config\.storage\energy_management_01KKCHQC1H76XNA33EYXJKFB4T', 'r', encoding='utf-8') as f:
    store = json.load(f)

data = store.get("data", {})
settings = data.get("settings", {})
print("SETTINGS:")
print(json.dumps(settings, indent=2))

print("PRICES SELL TODAY:")
print(json.dumps(data.get("prices_sell", {}), indent=2))

print("PRICES SELL TOMORROW:")
print(json.dumps(data.get("prices_sell_tomorrow", {}), indent=2))
