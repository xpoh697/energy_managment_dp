import os

ha_dir = r"\\192.168.100.5\config"
if os.path.exists(ha_dir):
    print("Files in HA config:")
    for f in os.listdir(ha_dir):
        if "log" in f or "db" in f:
            print(f)
else:
    print("HA config directory not found")
