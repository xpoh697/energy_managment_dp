import json

with open(r'\\192.168.100.5\config\.storage\energy_management_01KKCHQC1H76XNA33EYXJKFB4T', 'r', encoding='utf-8') as f:
    store = json.load(f)

data = store.get("data", {})
profile_data = data.get("consumption_base", {})

print("CONSUMPTION BASE PROFILE VALUES:")
for h in range(24):
    sh = str(h)
    history = profile_data.get(sh, [])
    valid_vals = [item.get('v', 0.0) for item in history[-14:]] if history else []
    avg = sum(valid_vals) / len(valid_vals) if valid_vals else 0.0
    print(f"  Hour {h:02d}: {avg:.3f} kW")
