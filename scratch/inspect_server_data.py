import json
import os
import datetime

with open(r'\\192.168.100.5\config\.storage\energy_management_01KKCHQC1H76XNA33EYXJKFB4T', 'r', encoding='utf-8') as f:
    store = json.load(f)

data = store.get("data", {})
sensor_last_values = data.get("sensor_last_values", {})

print("SOLCAST FORECAST SENSORS:")
for k, v in sensor_last_values.items():
    if "solcast" in k:
        print(f"  {k}: {v}")

print("\nOTHER KEY SENSORS:")
for k in ["sensor.inverter_battery", "sensor.inverter_battery_capacity", "sensor.battery_voltage"]:
    print(f"  {k}: {sensor_last_values.get(k)}")

# Print raw profiles today remaining
prof_gen = data.get("generation", {})
print("\nHISTORICAL PROFILE GENERATION:")
total_gen = 0.0
for h in range(24):
    history = prof_gen.get(str(h), [])
    valid_vals = [item.get('v', 0.0) for item in history[-14:]] if history else []
    val = sum(valid_vals) / len(valid_vals) if valid_vals else 0.0
    total_gen += val
    print(f"  {h:02d}:00: {val:.3f} kW")
print(f"Total historical generation: {total_gen:.3f} kWh")
