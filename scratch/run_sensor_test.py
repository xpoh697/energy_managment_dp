import sys
import os
import json

sys.path.insert(0, os.path.abspath('.'))
sys.path.insert(0, os.path.abspath('scratch'))

import mock_ha
import custom_components.energy_management.sensor as em_sensor

with open(r'\\192.168.100.5\config\.storage\core.config_entries', encoding='utf-8') as f:
    d = json.load(f)['data']['entries']
entry_data = [e for e in d if e['domain']=='energy_management'][0]

class MockEntry:
    def __init__(self, data, options):
        self.data = data
        self.options = options
        self.entry_id = "test_entry"

entry = MockEntry(entry_data['data'], entry_data['options'])
manager = em_sensor.EnergyProfileManager(mock_ha.MagicMock(), entry)
manager.settings = {}

print("=== REAL SENSOR.PY TRANSLATION TEST ===")
modes_to_test = ["GRID_CHG", "PAID_IMP", "DIS", "PV_CHG", "SOL", "SELF_CON", "GRID", "IDLE"]
for mode in modes_to_test:
    res = manager.translate_dp_mode(mode)
    print(f"translate_dp_mode({mode}) -> {res}")
