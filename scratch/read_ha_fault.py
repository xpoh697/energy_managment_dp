import os
import sys
sys.stdout.reconfigure(encoding='utf-8')

path = os.path.join(r"\\192.168.100.5\config", "home-assistant.log.fault")
if os.path.exists(path):
    print("Reading home-assistant.log.fault...")
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    print(content[:5000])
else:
    print("home-assistant.log.fault not found")
