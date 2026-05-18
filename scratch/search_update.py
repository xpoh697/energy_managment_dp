import sys
sys.stdout.reconfigure(encoding='utf-8')

with open("custom_components/energy_management/sensor.py", "r", encoding="utf-8") as f:
    for i, line in enumerate(f, 1):
        if "sell_strat" in line or "buy_strat" in line or "update" in line:
            if "def " in line or "=" in line:
                print(f"{i}: {line.strip()}")
