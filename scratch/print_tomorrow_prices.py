import json
import os
import datetime

with open(r'\\192.168.100.5\config\.storage\energy_management_01KKCHQC1H76XNA33EYXJKFB4T', 'r', encoding='utf-8') as f:
    store = json.load(f)

data = store.get("data", {})
settings = data.get("settings", {})
prices_sell = data.get("prices_sell", {})
prices_buy = data.get("prices_buy", {})

# Tomorrow's date
now = datetime.datetime.now()
tom = now + datetime.timedelta(days=1)
tom_str = tom.strftime("%Y-%m-%d")

print(f"Price Sell Only PV (price_sell_only_pv): {settings.get('price_sell_only_pv')}")
print(f"Sale PV No Bat Max Hour (sale_pv_no_bat_max_hour): {settings.get('sale_pv_no_bat_max_hour')}")
print(f"Tomorrow's Date: {tom_str}")

print("\nTOMORROW'S PRICES:")
print("Hour | Sell Price | Buy Price")
print("-" * 30)
tom_sell = prices_sell.get(tom_str, {})
tom_buy = prices_buy.get(tom_str, {})

for h in range(24):
    p_sell = tom_sell.get(str(h))
    if p_sell is None:
        p_sell = tom_sell.get(h)
    p_buy = tom_buy.get(str(h))
    if p_buy is None:
        p_buy = tom_buy.get(h)
    print(f"{h:02d}:00 | {p_sell} | {p_buy}")
