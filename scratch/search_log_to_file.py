import sys
sys.stdout.reconfigure(encoding='utf-8')

with open("custom_components/energy_management/sensor.py", "r", encoding="utf-8") as f:
    for i, line in enumerate(f, 1):
        if "log_to_file" in line:
            print(f"{i}: {line.strip()}")
