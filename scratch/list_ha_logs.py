import os

config_path = r'\\192.168.100.5\config'
if os.path.exists(config_path):
    print("Files in HA config directory:")
    for f in os.listdir(config_path):
        if f.endswith('.log'):
            print(f"  {f} ({os.path.getsize(os.path.join(config_path, f))} bytes)")
else:
    print("HA config path not accessible")
