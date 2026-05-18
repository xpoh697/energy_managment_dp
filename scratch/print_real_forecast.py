import sys
import json
sys.stdout.reconfigure(encoding='utf-8')

with open(r'\\192.168.100.5\config\.storage\energy_management_01KKCHQC1H76XNA33EYXJKFB4T', 'r', encoding='utf-8') as f:
    store = json.load(f)

store_data = store.get("data", {})
sensor_last_values = store_data.get("sensor_last_values", {})
print("SOLCAST SENSORS:")
for k, v in sensor_last_values.items():
    if "forecast" in k or "solcast" in k:
        print(f"{k}: {v}")
