import os
ha_dir = r"\\192.168.100.5\config"
if os.path.exists(ha_dir):
    print("All log files:")
    for f in os.listdir(ha_dir):
        if f.endswith(".log") or "home-assistant" in f:
            print(f)
else:
    print("HA config directory not found")
