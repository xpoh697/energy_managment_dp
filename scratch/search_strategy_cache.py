import sys
sys.stdout.reconfigure(encoding='utf-8')

with open("custom_components/energy_management/strategy_sell.py", "r", encoding="utf-8") as f:
    for i, line in enumerate(f, 1):
        if "def get_market_strategy" in line or "cache" in line:
            print(f"{i}: {line.strip()}")
