import os, sys
sys.stdout.reconfigure(encoding='utf-8')

log_path = r'\\192.168.100.5\config\home-assistant.log'
if os.path.exists(log_path):
    print("Found home-assistant.log. Searching for StrategySell and SimSolar...")
    with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            if "StrategySell" in line or "SimSolar" in line or "SimDeficit" in line or "energy_management" in line:
                # print only relevant warnings, debug, etc.
                if any(x in line for x in ["DEBUG", "WARNING", "ERROR", "CRITICAL"]):
                    print(line.strip())
else:
    print("home-assistant.log not found")
