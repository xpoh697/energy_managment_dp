import sys
import json
sys.stdout.reconfigure(encoding='utf-8')

with open(r'\\192.168.100.5\config\.storage\energy_management_01KKCHQC1H76XNA33EYXJKFB4T', 'r', encoding='utf-8') as f:
    store = json.load(f)

store_data = store.get("data", {})
gen_data = store_data.get("generation", {})
print("TODAY GENERATION ACTUALS:")
for h in range(24):
    history = gen_data.get(str(h), [])
    last_v = history[-1].get("v") if history and isinstance(history[-1], dict) else (history[-1] if history else 0.0)
    print(f"{h:02d}: {last_v}")
