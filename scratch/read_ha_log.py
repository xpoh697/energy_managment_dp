import os

log_path = r'\\192.168.100.5\config\home-assistant.log'
if os.path.exists(log_path):
    print("Reading home-assistant.log...")
    with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
    
    print("\nLATEST 100 LINES WITH energy_management:")
    count = 0
    for line in reversed(lines):
        if "energy_management" in line or "custom_components" in line:
            print(line.strip())
            count += 1
            if count >= 100:
                break
else:
    print("home-assistant.log not found")
