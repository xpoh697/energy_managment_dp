import sys
sys.stdout.reconfigure(encoding='utf-8')

import types
from unittest.mock import MagicMock
import datetime
import importlib.machinery
import json
import os

ha_pkg = types.ModuleType("homeassistant")
ha_pkg.__path__ = []
sys.modules["homeassistant"] = ha_pkg

ha_pkg_comp = types.ModuleType("homeassistant.components")
ha_pkg_comp.__path__ = []
sys.modules["homeassistant.components"] = ha_pkg_comp

ha_util_pkg = types.ModuleType("homeassistant.util")
ha_util_pkg.__path__ = []
sys.modules["homeassistant.util"] = ha_util_pkg

mock_dt = MagicMock()
mock_now = datetime.datetime(2026, 5, 18, 17, 0, 0)
mock_dt.now = lambda: mock_now
sys.modules["homeassistant.util.dt"] = mock_dt

class DummyLoader:
    def create_module(self, spec): return sys.modules.get(spec.name)
    def exec_module(self, module): pass
class MockFinder:
    def find_spec(self, fullname, path, target=None):
        if fullname.startswith("homeassistant"):
            m = sys.modules.get(fullname)
            if m is None:
                m = MagicMock()
                if fullname in ["homeassistant.helpers", "homeassistant.config_entries"]:
                    m.__path__ = []
                sys.modules[fullname] = m
            return importlib.machinery.ModuleSpec(fullname, DummyLoader())
        return None
sys.meta_path.insert(0, MockFinder())

sys.path.append(os.path.abspath('.'))
sys.path.append(os.path.abspath('./custom_components'))

with open(r'\\192.168.100.5\config\.storage\energy_management_01KKCHQC1H76XNA33EYXJKFB4T', 'r', encoding='utf-8') as f:
    store = json.load(f)

store_data = store.get("data", {})

from custom_components.energy_management.sensor import EnergyProfileManager

# Let's instantiate the real manager and run async_update_global_plan!
class MockHass:
    def __init__(self):
        self.states = MagicMock()
        
manager = EnergyProfileManager()
manager.hass = MockHass()
manager.entry = MagicMock()
manager.entry.data = store_data.get("settings", {})
manager.data = store_data
manager.power_history = []
manager.deduct_settings = {}
manager.power_load_sensors = []
manager.power_gen_sensors = []
manager.battery_power_sensor = None
manager.grid_power_sensor = None
manager.price_buy_sensors = []
manager.generation_sensors = []
manager._advice = {}

import asyncio
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

# Run the heuristic and DP plan calculation
loop.run_until_complete(manager.async_update_global_plan())

print("\n--- HEURISTIC HOURLY DATA ---")
for h_data in manager.heuristic_hourly_data:
    time_str = h_data.get("time")
    mode = h_data.get("mode")
    target_soc = h_data.get("target_soc")
    price = h_data.get("price")
    print(f"  {time_str}: {mode} | Target SOC: {target_soc}% | Price: {price}")
