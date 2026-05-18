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
mock_now = datetime.datetime(2026, 5, 17, 13, 51, 0)
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

from custom_components.energy_management.strategy_sell import StrategySell
from custom_components.energy_management.strategy_buy import StrategyBuy
from custom_components.energy_management.dispatch_plan import EnergyLogicEngine

class MockManager:
    def __init__(self, store_data, live_soc):
        self.data = store_data
        self.custom_period = 14
        self.day_type = 6
        self.battery_soc_sensor = "sensor.inverter_battery"
        self.battery_capacity_sensor = "sensor.inverter_battery_capacity"
        self.battery_power_sensor = "sensor.battery_power"
        self.forecast_today_sensor = "sensor.forecast_today"
        self.forecast_tomorrow_sensor = "sensor.forecast_tomorrow"
        self.forecast_today_hourly_sensor = "sensor.forecast_today_hourly"
        self.forecast_tomorrow_hourly_sensor = "sensor.forecast_tomorrow_hourly"
        self.battery_voltage_sensor = "sensor.battery_voltage"
        self.manual_mode_overrides = {}
        self.live_soc = live_soc
        self.avg_gen_5m_kw = 0.0
        self.avg_load_5m_kw = 0.5
    def get_setting(self, name, default=None): return self.data.get("settings", {}).get(name, default)
    def log_to_file(self, msg): pass
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
    def get_predicted_profile(self, kind): return self.get_average_profile(kind, 14)
    def get_predicted_profile_tomorrow(self, kind): return self.get_average_profile(kind, 14)
    def get_occupancy_coefficient(self): return 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0
    def get_hourly_accuracy_coeff(self, hour): return 1.0, 1.0
    @property
    def hourly_manual_overrides(self): return {}
    def get_sunrise_hour(self): return 8
    def get_sunset_hour(self): return 20
    def get_market_strategy(self, mode):
        if mode == "sell": return self.sell_strat
        if mode == "buy": return self.buy_strat
        return {}

manager = MockManager(store_data, 62.0)
strategy_sell = StrategySell(manager)
strategy_buy = StrategyBuy(manager)

manager.sell_strat = strategy_sell.get_market_strategy("sell")
manager.buy_strat = strategy_buy.get_market_strategy("buy")

# Simulate a 24-hour global plan projection using the Logic Engine
print("SIMULATING GLOBAL PLAN FOR THE NEXT 24 HOURS:")
sim_soc = 62.0
now = datetime.datetime(2026, 5, 17, 13, 51, 0)

prof_gen = manager.get_predicted_profile("generation")
prof_cons = manager.get_predicted_profile("consumption_total")

# Calculate scaling factors
now_h = now.hour
f_today_val = manager.get_forecast_value(manager.forecast_today_sensor)
f_tomorrow_val = manager.get_forecast_value(manager.forecast_tomorrow_sensor)

hist_today_rem = sum(float(prof_gen.get(str(h), 0.0)) for h in range(now_h, 24))
scale_today = float(f_today_val / hist_today_rem) if (f_today_val is not None and hist_today_rem > 0.1) else 1.0

hist_tomorrow = sum(float(prof_gen.get(str(h), 0.0)) for h in range(24))
scale_tomorrow = float(f_tomorrow_val / hist_tomorrow) if (f_tomorrow_val is not None and hist_tomorrow > 0.1) else 1.0

for h_abs in range(24):
    dt_h = (now + datetime.timedelta(hours=h_abs)).replace(minute=0, second=0, microsecond=0)
    h_rel = str(dt_h.hour)
    
    # Scale generation
    raw_gen = float(prof_gen.get(h_rel, 0.0))
    if dt_h.date() == now.date():
        scaled_gen = raw_gen * scale_today
    elif dt_h.date() == (now.date() + datetime.timedelta(days=1)):
        scaled_gen = raw_gen * scale_tomorrow
    else:
        scaled_gen = raw_gen
        
    scaled_load = float(prof_cons.get(h_rel, 0.5))
    
    # Get mode
    mode, reason, is_buy, is_sell, t_soc = EnergyLogicEngine.get_mode_at(
        dt_now=dt_h,
        batt_soc=sim_soc,
        manager=manager,
        is_forecast=(h_abs > 0),
        abs_hour=(now.hour + h_abs),
        profiles={"gen": prof_gen, "cons": prof_cons},
        buy_strategy=manager.buy_strat,
        sell_strategy=manager.sell_strat
    )
    
    # Simulate battery charge/discharge for the next hour
    eff = 0.98
    p_bat = 0.0
    if is_buy:
        p_bat = 2.5 # dummy charge power
        sim_soc += (p_bat * eff / 17.0) * 100.0
    elif is_sell:
        # Get planned power
        planned_p = manager.sell_strat.get("raw_commands", {}).get(now.hour + h_abs, 0.0)
        p_bat = -planned_p
        sim_soc += (p_bat / (max(0.1, eff) * 17.0)) * 100.0
    else:
        # Self-consumption or solar excess
        surplus = scaled_gen - scaled_load
        if surplus > 0:
            sim_soc += (min(3.0, surplus) * eff / 17.0) * 100.0
        else:
            sim_soc += (max(-3.0, surplus) / (eff * 17.0)) * 100.0
            
    sim_soc = max(10.0, min(100.0, sim_soc))
    
    print(f"  Hour {dt_h.hour:02d}:00 | Mode: {mode:<12} | SOC: {sim_soc:5.1f}% | Reason: {reason}")
