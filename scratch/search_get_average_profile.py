import sys
sys.stdout.reconfigure(encoding='utf-8')

with open("custom_components/energy_management/sensor.py", "r", encoding="utf-8") as f:
    in_func = False
    for i, line in enumerate(f, 1):
        if "def get_average_profile" in line:
            in_func = True
        if in_func:
            print(f"{i}: {line.strip()}")
            if i > 2630: # let's just print a small range
                in_func = False
