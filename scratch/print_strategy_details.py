import json
import os

with open(r'\\192.168.100.5\config\.storage\energy_management_01KKCHQC1H76XNA33EYXJKFB4T', 'r', encoding='utf-8') as f:
    store = json.load(f)

data = store.get("data", {})
sensor_last_values = data.get("sensor_last_values", {})

# Let's print out what strategies are cached
sell_strat_str = sensor_last_values.get("sensor.energy_management_market_sell_strategy")
if not sell_strat_str:
    # Let's search all keys for something containing "sell"
    for k in sensor_last_values.keys():
        if "sell" in k or "strategy" in k:
            print(f"Potential key: {k}")

print("\nLet's print the entire raw store structure keys:")
for k in sorted(data.keys()):
    print(f"  {k}")
