import json
import os

restore_path = r'\\192.168.100.5\config\.storage\core.restore_state'
if os.path.exists(restore_path):
    print("Found core.restore_state! Searching for energy_management sensors...")
    with open(restore_path, 'r', encoding='utf-8') as f:
        store = json.load(f)
    
    for item in store.get("data", []):
        entity_id = item.get("state", {}).get("entity_id", "")
        if "energy_management" in entity_id:
            print(f"\nENTITY: {entity_id}")
            print(f"  State: {item.get('state', {}).get('state')}")
            attrs = item.get("state", {}).get("attributes", {})
            for k in ["strategy_decision", "arbitrage_decision", "limit_reason", "projected_soc_morning", "projected_soc_after_sale", "projected_soc_at_sale_start", "debug_surplus", "arbitrage_sell_debug"]:
                if k in attrs:
                    print(f"  {k}: {attrs[k]}")
else:
    print("core.restore_state not found")
