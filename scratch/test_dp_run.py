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
mock_now = datetime.datetime(2026, 5, 18, 8, 20, 0)
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

from custom_components.energy_management.strategy_dp import DPPlanner

class MockManager:
    def __init__(self, store_data, live_soc):
        self.data = store_data
        self.custom_period = 14
        self.day_type = 6
        self.battery_soc_sensor = "sensor.inverter_battery"
        self.battery_capacity_sensor = "sensor.inverter_battery_capacity"
        self.forecast_today_sensor = "sensor.forecast_today"
        self.forecast_tomorrow_sensor = "sensor.forecast_tomorrow"
        self.forecast_today_hourly_sensor = "sensor.forecast_today_hourly"
        self.forecast_tomorrow_hourly_sensor = "sensor.forecast_tomorrow_hourly"
        self.battery_voltage_sensor = "sensor.battery_voltage"
        self.manual_mode_overrides = {}
        self.live_soc = live_soc
        self.now = mock_now
    def get_setting(self, name, default=None): return self.data.get("settings", {}).get(name, default)
    def get_battery_state(self, soc_default=0.0): 
        return self.live_soc, 17.0, self.live_soc/100.0 * 17.0
    def get_sensor_float(self, name, default=0.0): return float(self.data.get("sensor_last_values", {}).get(name, default))
    def get_forecast_value(self, name):
        if "today" in name: 
            return 7.33
        if "tomorrow" in name: 
            return float(self.data.get("sensor_last_values", {}).get("sensor.solcast_pv_forecast_forecast_tomorrow", 42.0))
        return 0.0
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
    def get_price(self, kind, date_str, hour): 
        p_dict = self.data.get(f"prices_{kind}", {}).get(date_str, {})
        val = p_dict.get(str(hour))
        if val is None:
            val = p_dict.get(hour)
        return val
    def _get_prices(self, kind):
        # mock fetching prices dict
        date_today = mock_now.strftime("%Y-%m-%d")
        date_tomorrow = (mock_now + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        res = {}
        p_today = self.data.get(kind, {}).get(date_today, {})
        p_tomorrow = self.data.get(kind, {}).get(date_tomorrow, {})
        for h in range(24):
            res[str(h)] = p_today.get(str(h), 0.5)
            res[str(h+24)] = p_tomorrow.get(str(h), 0.5)
        return res
    def get_predicted_profile(self, kind): return self.get_average_profile(kind, 14)
    def get_predicted_profile_tomorrow(self, kind): return self.get_average_profile(kind, 14)
    def get_occupancy_coefficient(self): return 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0
    def get_hourly_accuracy_coeff(self, hour): return 1.0, 1.0
    @property
    def hourly_manual_overrides(self): return {}
    def get_sunrise_hour(self): return 8
    def get_sunset_hour(self): return 20

manager = MockManager(store_data, 62.0)
planner = DPPlanner(manager)

snapshot = {
    "soc": 62.0,
    "capacity": 17.0,
    "prices_buy": manager._get_prices("prices_buy"),
    "prices_sell": manager._get_prices("prices_sell")
}

advice = planner.get_dp_advice(snapshot)
print("DP ADVICE RESULT SUCCESS:")
print(f"  best_value: {advice.get('best_value')}")
print(f"  formatted_plan keys count: {len(advice.get('formatted_plan', {}))}")
print(f"  first 3 hours of plan:")
sorted_plan = sorted(advice.get("plan", {}).items())
for k, v in sorted_plan[:3]:
    print(f"    {k}: {v}")
