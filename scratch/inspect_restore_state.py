import json
import os
import sys
sys.stdout.reconfigure(encoding='utf-8')

path = r"\\192.168.100.5\config\.storage\core.restore_state"
if os.path.exists(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    print("Searching core.restore_state...")
    for entry in data.get("data", []):
        state_obj = entry.get("state", {})
        entity_id = state_obj.get("entity_id", "")
        if "01KKCHQC1" in entity_id or "inverter_mode" in entity_id or "inverter" in entity_id:
            print(f"Entity: {entity_id}")
            print(f"  State: {state_obj.get('state')}")
            attrs = state_obj.get("attributes", {})
            print("  Attributes:")
            for k, v in attrs.items():
                if "hourly_data" in k or "planned_modes" in k:
                    print(f"    {k}: {str(v)[:150]}...")
                else:
                    print(f"    {k}: {v}")
else:
    print("core.restore_state not found")
