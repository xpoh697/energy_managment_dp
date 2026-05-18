import sys
import types
from unittest.mock import MagicMock
import datetime
import importlib.machinery

# Create mock homeassistant package
ha_pkg = types.ModuleType("homeassistant")
sys.modules["homeassistant"] = ha_pkg
ha_util_pkg = types.ModuleType("homeassistant.util")
sys.modules["homeassistant.util"] = ha_util_pkg
mock_dt = MagicMock()
mock_dt.now = lambda: datetime.datetime.now()
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
                sys.modules[fullname] = m
            return importlib.machinery.ModuleSpec(fullname, DummyLoader())
        return None
sys.meta_path.insert(0, MockFinder())

import json, os
sys.path.append(os.path.abspath('.'))
sys.path.append(os.path.abspath('./custom_components'))
from energy_management.strategy_base import StrategyEngine

class MockManager:
    def __init__(self, store_data):
        self.data = store_data
        self.custom_period = 14
        self.day_type = 6
        self.battery_soc_sensor = "sensor.inverter_battery"
        self.battery_capacity_sensor = "sensor.inverter_battery_capacity"
    def get_setting(self, name, default=None): return self.data.get("settings", {}).get(name, default)
    def get_battery_state(self, soc_default=0.0): return 58.9, 17.0, (58.9 / 100.0 * 17.0)
    def get_sensor_float(self, name, default=0.0): return float(self.data.get("sensor_last_values", {}).get(name, default))
    def get_forecast_value(self, name): return 0.0
    def get_forecast_hourly_distribution(self, name, date_str=None): return {}
    def get_forecast_hourly(self, name): return {}
    def get_average_profile(self, profile_type, days, day_type="all"):
        profile = {}
        profile_data = self.data.get(profile_type, {})
        for h in range(24):
            sh = str(h)
            history = profile_data.get(sh, [])
            valid_vals = [item.get('v', 0.0) for item in history[-days:]] if history else []
            profile[str(h)] = sum(valid_vals) / len(valid_vals) if valid_vals else 0.0
        return profile
    def get_price(self, kind, date_str, hour): return self.data.get(f"prices_{kind}", {}).get(date_str, {}).get(str(hour))
    def get_predicted_profile(self, kind): return self.get_average_profile(kind, 14)
    def get_predicted_profile_tomorrow(self, kind): return self.get_average_profile(kind, 14)
    def get_occupancy_coefficient(self): return 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0
    def get_hourly_accuracy_coeff(self, hour): return 1.0, 1.0
    @property
    def hourly_manual_overrides(self): return {}

with open(r'\\192.168.100.5\config\.storage\energy_management_01KKCHQC1H76XNA33EYXJKFB4T', 'r', encoding='utf-8') as f:
    store = json.load(f)

manager = MockManager(store.get("data", {}))
engine = StrategyEngine(manager)

commands = {10: 3.712}
mode_overrides = {}

now = datetime.datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
sim_range = list(range(9, 13))

simulated_soc, history_log, overflow = engine.run_soc_simulation(
    start_soc=58.9, sim_range=sim_range, now=now, commands=commands, mode_overrides=mode_overrides
)

for h in sim_range:
    log_item = history_log.get(h, {})
    print(f"Hour {h:02d}:00 | Mode: {log_item.get('mode', 'N/A'):<15} | StartSOC: {log_item.get('soc_start', 0.0):.1f}% | EndSOC: {log_item.get('soc_end', 0.0):.1f}% | ReqP: {log_item.get('req_p', 0.0):.2f} kW | NetP: {log_item.get('net_p_bat', 0.0):.2f} kW")
