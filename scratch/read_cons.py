import json

with open(r'\\192.168.100.5\config\.storage\energy_management_01KKCHQC1H76XNA33EYXJKFB4T', 'r', encoding='utf-8') as f:
    store = json.load(f)

data = store.get("data", {})
# Let's get the average profile of consumption_total
profile_data = data.get("consumption_total", {})
profile = {}
days = 14
for h in range(24):
    sh = str(h)
    history = profile_data.get(sh, [])
    valid_vals = [item.get('v', 0.0) for item in history[-days:]] if history else []
    profile[str(h)] = sum(valid_vals) / len(valid_vals) if valid_vals else 0.0

print("CONSUMPTION PROFILE:")
print(json.dumps(profile, indent=2))
