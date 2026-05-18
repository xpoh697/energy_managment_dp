import sys
sys.stdout.reconfigure(encoding='utf-8')

with open("custom_components/energy_management/sensor.py", "r", encoding="utf-8") as f:
    in_func = False
    for i, line in enumerate(f, 1):
        if "def get_battery_state" in line:
            in_func = True
        if in_func:
            print(f"{i}: {line.strip()}")
            if "return" in line and not line.strip().startswith("#"):
                in_func = False
