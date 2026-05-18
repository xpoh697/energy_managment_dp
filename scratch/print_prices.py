import json

with open(r'\\192.168.100.5\config\.storage\energy_management_01KKCHQC1H76XNA33EYXJKFB4T', 'r', encoding='utf-8') as f:
    store = json.load(f)

store_data = store.get("data", {})
prices_sell = store_data.get("prices_sell", {})
prices_buy = store_data.get("prices_buy", {})

print("PRICES SELL:")
for k, v in prices_sell.items():
    print(f"  {k}: {v}")

print("\nPRICES BUY:")
for k, v in prices_buy.items():
    print(f"  {k}: {v}")
