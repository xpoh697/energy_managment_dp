import os
import sys
import json
sys.stdout.reconfigure(encoding='utf-8')

# Let's locate the store file
path = r"\\192.168.100.5\config\.storage\energy_management_store"
if os.path.exists(path):
    print("Found store file. Reading...")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    advice = data.get("dp_advice_stable", {})
    if not advice:
        # Check settings
        advice = data.get("settings", {}).get("dp_advice_stable", {})
        
    print(f"dp_advice_stable type: {type(advice).__name__}")
    if isinstance(advice, dict):
        print(f"Keys: {list(advice.keys())}")
        plan_by_ts = advice.get("plan_by_timestamp", {})
        print(f"plan_by_timestamp type: {type(plan_by_ts).__name__}")
        if isinstance(plan_by_ts, dict):
            print(f"Number of slots: {len(plan_by_ts)}")
            # Print first 5 slots
            for i, (k, v) in enumerate(list(plan_by_ts.items())[:5]):
                print(f"  {k}: {v}")
    else:
        print(f"Value: {advice}")
else:
    print("Store file not found")
