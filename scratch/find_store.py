import os
import sys
sys.stdout.reconfigure(encoding='utf-8')

ha_dir = r"\\192.168.100.5\config"
print("Searching in HA config...")
if os.path.exists(ha_dir):
    # check .storage directory
    storage_dir = os.path.join(ha_dir, ".storage")
    if os.path.exists(storage_dir):
        print(f"Found .storage directory: {storage_dir}")
        for f in os.listdir(storage_dir):
            if "energy" in f or "store" in f:
                print(f"  {f}")
    else:
        print(".storage directory not found")
else:
    print("HA config not found")
