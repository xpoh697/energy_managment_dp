import json

with open(r'\\192.168.100.5\config\.storage\energy_management_01KKCHQC1H76XNA33EYXJKFB4T', 'r', encoding='utf-8') as f:
    store = json.load(f)

data = store.get("data", {})
sensor_last_values = data.get("sensor_last_values", {})
print("SENSOR LAST VALUES:")
print(json.dumps(sensor_last_values, indent=2))
