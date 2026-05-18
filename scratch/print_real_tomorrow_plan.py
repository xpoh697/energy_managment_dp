import sys
import os
import datetime
import json
import asyncio
import traceback
sys.stdout.reconfigure(encoding='utf-8')

# Mock HA properly with dynamic attributes
import types
from unittest.mock import MagicMock
import importlib.machinery

class RestoreEntity: pass
class SensorEntity: pass
class BinarySensorEntity: pass
class SwitchEntity: pass
class NumberEntity: pass
class HomeAssistantView: pass

class FlexibleModule(types.ModuleType):
    def __getattr__(self, name):
        if name == "SensorEntity": return SensorEntity
        if name == "BinarySensorEntity": return BinarySensorEntity
        if name == "SwitchEntity": return SwitchEntity
        if name == "NumberEntity": return NumberEntity
        if name == "HomeAssistantView": return HomeAssistantView
        if name == "RestoreEntity": return RestoreEntity
        return MagicMock()

# Setup modules
for module_name in [
    "homeassistant",
    "homeassistant.components",
    "homeassistant.util",
    "homeassistant.helpers",
    "homeassistant.helpers.restore_state",
    "homeassistant.components.sensor",
    "homeassistant.components.binary_sensor",
    "homeassistant.components.switch",
    "homeassistant.components.number",
    "homeassistant.components.http",
    "homeassistant.config_entries",
    "homeassistant.helpers.entity_platform",
    "homeassistant.helpers.config_validation"
]:
    m = FlexibleModule(module_name)
    m.__path__ = []
    sys.modules[module_name] = m

# Mock dt properly with return_value
mock_now = datetime.datetime(2026, 5, 17, 18, 30, 0)
mock_dt = MagicMock()
mock_dt.now = lambda: mock_now
sys.modules["homeassistant.util.dt"] = mock_dt

# Fix python module import resolution
ha_util = sys.modules["homeassistant.util"]
ha_util.dt = mock_dt

class DummyLoader:
    def create_module(self, spec): return sys.modules.get(spec.name)
    def exec_module(self, module): pass
class MockFinder:
    def find_spec(self, fullname, path, target=None):
        if fullname.startswith("homeassistant"):
            m = sys.modules.get(fullname)
            if m is None:
                m = FlexibleModule(fullname)
                m.__path__ = []
                sys.modules[fullname] = m
            return importlib.machinery.ModuleSpec(fullname, DummyLoader())
        return None
sys.meta_path.insert(0, MockFinder())

sys.path.append(os.path.abspath('.'))
sys.path.append(os.path.abspath('./custom_components'))

from custom_components.energy_management.sensor import EnergyProfileManager

with open(r'\\192.168.100.5\config\.storage\energy_management_01KKCHQC1H76XNA33EYXJKFB4T', 'r', encoding='utf-8') as f:
    store = json.load(f)

store_data = store.get("data", {})

class FakeHass:
    def __init__(self):
        self.config = MagicMock()
        self.config.path = lambda p: os.path.join(r"\\192.168.100.5\config", p)
        self.states = MagicMock()
        self.states.get = lambda entity_id: None
    def async_add_executor_job(self, target, *args):
        return target(*args)

class RealMockManager(EnergyProfileManager):
    def __init__(self, hass, store_data):
        self.hass = hass
        self.data = store_data
        self.entry = MagicMock()
        self.entry.data = {"holiday_as_weekend": False}
        self.manual_mode_overrides = {}
        self.hourly_manual_overrides = {}
        
        self._now_override = datetime.datetime(2026, 5, 17, 18, 30, 0)
        
        self.battery_soc_sensor = "sensor.inverter_battery"
        self.battery_capacity_sensor = "sensor.inverter_battery_capacity"
        self.forecast_today_sensor = "sensor.forecast_today"
        self.forecast_tomorrow_sensor = "sensor.forecast_tomorrow"
        self.forecast_today_hourly_sensor = "sensor.forecast_today_hourly"
        self.forecast_tomorrow_hourly_sensor = "sensor.forecast_tomorrow_hourly"
        self.battery_voltage_sensor = "sensor.battery_voltage"
        
        from custom_components.energy_management.strategy_sell import StrategySell
        from custom_components.energy_management.strategy_buy import StrategyBuy
        self.strategy_engine = StrategySell(self)
        self.buy_strat_engine = StrategyBuy(self)
        
    @property
    def now(self):
        return self._now_override
        
    @property
    def custom_period(self):
        return 14
        
    @property
    def day_type(self):
        return 6
        
    @property
    def fixed_strategy_data(self):
        return {"buy": {}, "sell": {}}
        
    def get_setting(self, name, default=None): 
        return self.data.get("settings", {}).get(name, default)
        
    def get_battery_state(self, soc_default=0.0): 
        return 57.0, 17.0, 9.69
        
    def get_sensor_float(self, name, default=0.0): 
        return float(self.data.get("sensor_last_values", {}).get(name, default))
        
    def get_forecast_value(self, name):
        if "today" in name: return 6.6
        if "tomorrow" in name: return 42.0
        return 0.0
        
    def get_forecast_hourly_distribution(self, name, date_str=None): 
        return {}
        
    def get_forecast_hourly(self, name): 
        return {}
        
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
        
    def get_predicted_profile(self, kind): 
        return self.get_average_profile(kind, 14)
        
    def get_occupancy_coefficient(self): 
        return 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0
        
    def get_hourly_accuracy_coeff(self, hour): 
        return 1.0, 1.0
        
    def get_sunrise_hour(self): return 8
    def get_sunset_hour(self): return 20

async def main():
    hass = FakeHass()
    manager = RealMockManager(hass, store_data)
    await manager.async_update_global_plan()
    
    plan = manager.global_plan
    print("SLOT # | DATETIME | SOC START | SOC END | PRICE SELL | GEN SCALED | LOAD | MODE | REASON")
    print("-" * 120)
    for i, s in enumerate(plan.slots):
        dt_obj = datetime.datetime.fromisoformat(s.dt_iso)
        print(f"{i:02d} | {dt_obj.strftime('%Y-%m-%d %H:00')} | {s.soc_start:.1f}% | {s.soc_end:.1f}% | {s.price_sell:.2f} | {s.gen_raw:.2f} | {s.load_total:.2f} | {s.mode} | {s.reason}")

asyncio.run(main())
