import sys
import json
import os
sys.stdout.reconfigure(encoding='utf-8')

restore_path = r"\\192.168.100.5\config\.storage\core.restore_state"
if os.path.exists(restore_path):
    with open(restore_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    for entity in data.get("data", []):
        state = entity.get("state", {})
        entity_id = state.get("entity_id")
        if entity_id and "energy_management" in entity_id:
            print(f"Entity: {entity_id}")
            print(f"State: {state.get('state')}")
            print("Attributes:")
            print(json.dumps(state.get("attributes"), indent=2))
            print("-" * 50)
else:
    print("core.restore_state not found!")
