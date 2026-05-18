import sys
sys.stdout.reconfigure(encoding='utf-8')

import types
from unittest.mock import MagicMock
import datetime
import importlib.machinery

# Create mock homeassistant package
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
# Mock now to return 13:00 today (May 17)
mock_now = datetime.datetime(2026, 5, 17, 13, 0, 0)
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
                # If it's a package path (like config_entries or components or helpers), give it a __path__
                if fullname in ["homeassistant.helpers", "homeassistant.config_entries"]:
                    m.__path__ = []
                sys.modules[fullname] = m
            return importlib.machinery.ModuleSpec(fullname, DummyLoader())
        return None
sys.meta_path.insert(0, MockFinder())

import json, os
sys.path.append(os.path.abspath('.'))
sys.path.append(os.path.abspath('./custom_components'))

# 1. Normal Import (to register parent package & handle relative imports)
from custom_components.energy_management.strategy_sell import StrategySell

# 2. Read and Patch the source code at runtime
with open("G:/systemair/energy_mamagment/custom_components/energy_management/strategy_sell.py", "r", encoding="utf-8") as f:
    code = f.read()

# Apply the distribution cap patch
old_target = """                        p_export = min(max_batt_p, rem_budget / duration)
                        
                        sell_commands[h] = round_f(p_export, 3) if p_export > 0.05 else 0.0"""

new_target = """                        # Cap distribution by hour's power cap from previous feedback loop
                        p_cap = h_power_caps.get(h, max_batt_p)
                        p_export = min(p_cap, rem_budget / duration)
                        
                        sell_commands[h] = round_f(p_export, 3) if p_export > 0.05 else 0.0"""

code = code.replace(old_target, new_target)

# Apply the epsilon creep / small cap protection patch
old_cap_update = """                            # If hour is limited by floor, cap it for the next iteration
                            if h_soc < h_floor + 0.1:
                                old_cap = h_power_caps.get(h_cmd, max_batt_p)
                                new_cap = max(0.0, p_real_dc + 0.01) # Small epsilon
                                if new_cap < old_cap:
                                    h_power_caps[h_cmd] = new_cap"""

new_cap_update = """                            # If hour is limited by floor, cap it for the next iteration
                            if h_soc < h_floor + 0.1:
                                old_cap = h_power_caps.get(h_cmd, max_batt_p)
                                new_cap = max(0.0, p_real_dc + 0.01) # Small epsilon
                                # Avoid epsilon creep / tiny phantom loads
                                if new_cap < 0.05:
                                    new_cap = 0.0
                                if new_cap < old_cap:
                                    h_power_caps[h_cmd] = new_cap"""

code = code.replace(old_cap_update, new_cap_update)

# Apply early convergence safety break
old_loop_start = """                for attempt in range(20): # v11.9.315: Increased iterations for complex cases
                    # --- Stage 2: Distribution Loop (TS 107) ---
                    rem_budget = float(target_budget_ac)"""

new_loop_start = """                prev_commands = {}
                for attempt in range(20): # v11.9.315: Increased iterations for complex cases
                    # --- Stage 2: Distribution Loop (TS 107) ---
                    rem_budget = float(target_budget_ac)"""

code = code.replace(old_loop_start, new_loop_start)

old_distribution = """                        sell_commands[h] = round_f(p_export, 3) if p_export > 0.05 else 0.0
                        rem_budget -= p_export * duration"""

new_distribution = """                        sell_commands[h] = round_f(p_export, 3) if p_export > 0.05 else 0.0
                        rem_budget -= p_export * duration
                    
                    # v12.0.89: Convergence optimization - break if commands are stable
                    if attempt > 0 and sell_commands == prev_commands:
                        break
                    prev_commands = dict(sell_commands)"""

code = code.replace(old_distribution, new_distribution)

# Execute patched code inside the original module namespace
exec(code, sys.modules["custom_components.energy_management.strategy_sell"].__dict__)
StrategySell = sys.modules["custom_components.energy_management.strategy_sell"].StrategySell

class MockManager:
    def __init__(self, store_data):
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
    def get_setting(self, name, default=None): return self.data.get("settings", {}).get(name, default)
    def get_battery_state(self, soc_default=0.0): return 57.0, 10.0, 5.7
    def get_sensor_float(self, name, default=0.0): return float(self.data.get("sensor_last_values", {}).get(name, default))
    def get_forecast_value(self, name):
        if "today" in name: return 6.6
        if "tomorrow" in name: return 42.0
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
    def get_predicted_profile(self, kind): return self.get_average_profile(kind, 14)
    def get_predicted_profile_tomorrow(self, kind): return self.get_average_profile(kind, 14)
    def get_occupancy_coefficient(self): return 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0
    def get_hourly_accuracy_coeff(self, hour): return 1.0, 1.0
    @property
    def hourly_manual_overrides(self): return {}
    def get_sunrise_hour(self): return 8
    def get_sunset_hour(self): return 20

with open(r'\\192.168.100.5\config\.storage\energy_management_01KKCHQC1H76XNA33EYXJKFB4T', 'r', encoding='utf-8') as f:
    store = json.load(f)

manager = MockManager(store.get("data", {}))
strategy = StrategySell(manager)

res = strategy.get_market_strategy("sell")

print("RESULT:")
print(json.dumps(res.get("arbitrage_sell_debug", {}), indent=2, ensure_ascii=False))
