import json

path = r'\\192.168.100.5\config\.storage\energy_management_01KKCHQC1H76XNA33EYXJKFB4T'
with open(path, 'r', encoding='utf-8') as f:
    store = json.load(f)

data = store.get("data", {})
generation = data.get("generation", {})
consumption_total = data.get("consumption_total", {})
consumption_base = data.get("consumption_base", {})

print("REAL PROFILES IN DATABASE:")
for h in range(17, 24):
    sh = str(h)
    gen_list = generation.get(sh, [])
    cons_list = consumption_total.get(sh, [])
    base_list = consumption_base.get(sh, [])
    
    g_val = gen_list[-1]['v'] if gen_list else 0.0
    c_val = cons_list[-1]['v'] if cons_list else 0.0
    b_val = base_list[-1]['v'] if base_list else 0.0
    
    print(f"  Hour {h:02d}:00: Gen={g_val:.2f}kW, ConsTotal={c_val:.2f}kW, ConsBase={b_val:.2f}kW")
