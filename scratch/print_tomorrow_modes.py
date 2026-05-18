import sys
import os
import datetime
import json
sys.stdout.reconfigure(encoding='utf-8')

# Mock HA
import types
from unittest.mock import MagicMock
import importlib.machinery

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
mock_now = datetime.datetime(2026, 5, 17, 18, 30, 0)
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

from custom_components.energy_management.strategy_sell import StrategySell
from custom_components.energy_management.dispatch_plan import EnergyLogicEngine

with open(r'\\192.168.100.5\config\.storage\energy_management_01KKCHQC1H76XNA33EYXJKFB4T', 'r', encoding='utf-8') as f:
    store = json.load(f)

store_data = store.get("data", {})

class MockManager:
    def __init__(self, store_data):
        self.data = store_data
        self.custom_period = 14
        self.day_type = 6
        self._now = mock_now
        self.battery_soc_sensor = "sensor.inverter_battery"
        self.battery_capacity_sensor = "sensor.inverter_battery_capacity"
        self.forecast_today_sensor = "sensor.forecast_today"
        self.forecast_tomorrow_sensor = "sensor.forecast_tomorrow"
        self.forecast_today_hourly_sensor = "sensor.forecast_today_hourly"
        self.forecast_tomorrow_hourly_sensor = "sensor.forecast_tomorrow_hourly"
        self.battery_voltage_sensor = "sensor.battery_voltage"
        self.manual_mode_overrides = {}
        self.buy_strat = {}
        self.sell_strat = {}
    @property
    def now(self):
        return self._now
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
    def get_market_strategy(self, kind):
        if kind == "buy": return self.buy_strat
        if kind == "sell": return self.sell_strat
        return {}

manager = MockManager(store_data)
strategy_sell = StrategySell(manager)
sell_strat = strategy_sell.get_market_strategy("sell")
manager.sell_strat = sell_strat

# Let's print out for tomorrow's morning hours what decisions get_mode_at produces!
tom = mock_now + datetime.timedelta(days=1)
tom_str = tom.strftime("%Y-%m-%d")

# Tomorrow absolute hour starts at 24.
# Let's simulate the SOC hourly projection starting at 100.0% tomorrow morning
soc = 100.0  # SOC tomorrow morning starts at 100%

shared_profiles = {
    "gen": manager.get_predicted_profile("generation"),
    "cons": manager.get_predicted_profile("consumption_total")
}

print("Hour | SOC | Gen | Load | price_sell_only_pv | is_before_limit | has_surplus | block_pv_no_bat | Mode | Reason")
print("-" * 115)

for h in range(5, 15):
    # absolute hour for tomorrow is 24 + h
    abs_h = 24 + h
    
    # We call get_mode_at with tomorrow's specific datetime
    dt_h = datetime.datetime(2026, 5, 18, h, 0, 0)
    
    mode, reason, is_b, is_s, t_soc = EnergyLogicEngine.get_mode_at(
        dt_now=dt_h,
        batt_soc=soc,
        manager=manager,
        is_forecast=True,
        abs_hour=abs_h,
        profiles=shared_profiles,
        buy_strategy={},
        sell_strategy=sell_strat
    )
    
    p_gen = shared_profiles["gen"].get(str(h), 0.0)
    p_cons = shared_profiles["cons"].get(str(h), 0.5)
    
    # Re-calculate variables for display
    price_sell_only_pv = float(manager.get_setting("price_sell_only_pv", 999.0) or 999.0)
    sale_pv_no_bat_max_hour = float(manager.get_setting("sale_pv_no_bat_max_hour", 13.0) or 13.0)
    sim_h = abs_h % 24
    is_before_limit_hour = bool(sim_h < sale_pv_no_bat_max_hour)
    has_surplus = bool(p_gen > (p_cons + 0.05))
    latest_charge_start = (sell_strat.get("sell_simulation") or {}).get("latest_charge_start", sim_h)
    _block_sale_pv_no_bat = bool(sim_h >= latest_charge_start)
    
    print(f"{h:02d}:00 | {soc:.1f}% | {p_gen:.2f} | {p_cons:.2f} | {price_sell_only_pv:.2f} | {is_before_limit_hour} | {has_surplus} | {_block_sale_pv_no_bat} | {mode} | {reason}")
    
    # Simple SOC update for next step
    eff = 0.98
    b_cap = 17.0
    if mode == "sale_pv_no_bat":
        p_actual = 0.0 # battery is completely idle in sale_pv_no_bat in real life!
    elif mode == "sale_pv":
        net = p_gen - p_cons
        p_actual = net
    else:
        p_actual = 0.0
    delta_kwh = p_actual * (eff if p_actual > 0 else (1.0/eff))
    soc = max(0.0, min(100.0, soc + (delta_kwh / b_cap * 100.0)))
