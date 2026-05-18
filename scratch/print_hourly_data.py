import json

with open(r'\\192.168.100.5\config\.storage\energy_management_01KKCHQC1H76XNA33EYXJKFB4T', 'r', encoding='utf-8') as f:
    store = json.load(f)

# Find the entity in the storage or print the attributes
# The custom component stores hourly_manual_overrides and potentially other things.
# Wait, let's search if the hourly_data is saved in the store, or if it is only in the state machine (in memory).
# Yes, the hourly_data is in the attributes of sensor.energy_management, which is not persisted in the .storage file.
# But wait, does Home Assistant store states in the DB? Yes, home-assistant_v2.db!
# Let's check if we can query the latest state of sensor.energy_management from home-assistant_v2.db!
