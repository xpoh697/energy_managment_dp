import sys
sys.stdout.reconfigure(encoding='utf-8')

import logging
logging.basicConfig(level=logging.ERROR, format='%(levelname)s:%(name)s:%(message)s')

import types
import datetime
import importlib.machinery
import json
import os
import traceback

# 1. Setup mock modules to avoid metaclass conflicts
ha_pkg = types.ModuleType("homeassistant")
ha_pkg.__path__ = []
sys.modules["homeassistant"] = ha_pkg

core_mod = types.ModuleType("homeassistant.core")
def dummy_decorator(func): return func
core_mod.callback = dummy_decorator
core_mod.HomeAssistant = lambda: None
core_mod.State = type("State", (), {})
sys.modules["homeassistant.core"] = core_mod

class MockEntity: pass
class MockRestoreEntity: pass
class MockSensorEntity: pass
class MockButtonEntity: pass
class MockSwitchEntity: pass
class MockSelectEntity: pass
class MockDeviceInfo:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

# Helpers
helpers_pkg = types.ModuleType("homeassistant.helpers")
helpers_pkg.__path__ = []
sys.modules["homeassistant.helpers"] = helpers_pkg

restore_state_mod = types.ModuleType("homeassistant.helpers.restore_state")
restore_state_mod.RestoreEntity = MockRestoreEntity
sys.modules["homeassistant.helpers.restore_state"] = restore_state_mod

entity_mod = types.ModuleType("homeassistant.helpers.entity")
entity_mod.Entity = MockEntity
entity_mod.DeviceInfo = MockDeviceInfo
sys.modules["homeassistant.helpers.entity"] = entity_mod

dr_mod = types.ModuleType("homeassistant.helpers.device_registry")
dr_mod.DeviceInfo = MockDeviceInfo
sys.modules["homeassistant.helpers.device_registry"] = dr_mod

storage_mod = types.ModuleType("homeassistant.helpers.storage")
storage_mod.Store = type("Store", (), {})
sys.modules["homeassistant.helpers.storage"] = storage_mod

event_mod = types.ModuleType("homeassistant.helpers.event")
event_mod.async_track_state_change_event = lambda *args, **kwargs: None
event_mod.async_track_time_change = lambda *args, **kwargs: None
event_mod.async_track_time_interval = lambda *args, **kwargs: None
sys.modules["homeassistant.helpers.event"] = event_mod

# Components
comp_pkg = types.ModuleType("homeassistant.components")
comp_pkg.__path__ = []
sys.modules["homeassistant.components"] = comp_pkg

sensor_mod = types.ModuleType("homeassistant.components.sensor")
sensor_mod.__path__ = []
sensor_mod.SensorEntity = MockSensorEntity
sensor_mod.SensorDeviceClass = type("SensorDeviceClass", (), {"ENERGY": "energy", "BATTERY": "battery"})
sensor_mod.SensorStateClass = type("SensorStateClass", (), {"MEASUREMENT": "measurement", "TOTAL_INCREASING": "total_increasing"})
sys.modules["homeassistant.components.sensor"] = sensor_mod

http_mod = types.ModuleType("homeassistant.components.http")
http_mod.HomeAssistantView = MockEntity
sys.modules["homeassistant.components.http"] = http_mod

button_mod = types.ModuleType("homeassistant.components.button")
button_mod.ButtonEntity = MockButtonEntity
sys.modules["homeassistant.components.button"] = button_mod

switch_mod = types.ModuleType("homeassistant.components.switch")
switch_mod.SwitchEntity = MockSwitchEntity
sys.modules["homeassistant.components.switch"] = switch_mod

select_mod = types.ModuleType("homeassistant.components.select")
select_mod.SelectEntity = MockSelectEntity
sys.modules["homeassistant.components.select"] = select_mod

util_pkg = types.ModuleType("homeassistant.util")
util_pkg.__path__ = []
sys.modules["homeassistant.util"] = util_pkg

# DateTime mock
mock_dt = types.ModuleType("homeassistant.util.dt")
mock_now = datetime.datetime.now(datetime.timezone.utc)
mock_dt.now = lambda: datetime.datetime.now(datetime.timezone.utc)
mock_dt.parse_datetime = lambda s: datetime.datetime.fromisoformat(s.replace("Z", "+00:00")) if s else None
mock_dt.as_local = lambda d: d
sys.modules["homeassistant.util.dt"] = mock_dt

# Custom Finder to bypass homeassistant imports
class DummyLoader:
    def create_module(self, spec): return sys.modules.get(spec.name)
    def exec_module(self, module): pass
class MockFinder:
    def find_spec(self, fullname, path, target=None):
        if fullname.startswith("homeassistant"):
            if fullname in sys.modules:
                return importlib.machinery.ModuleSpec(fullname, DummyLoader())
            parts = fullname.split(".")
            if len(parts) > 3:
                # Class or helper import - let python search parent attributes
                return None
            m = types.ModuleType(fullname)
            m.__path__ = []
            sys.modules[fullname] = m
            return importlib.machinery.ModuleSpec(fullname, DummyLoader())
        return None
sys.meta_path.insert(0, MockFinder())

sys.path.append(os.path.abspath('.'))
sys.path.append(os.path.abspath('./custom_components'))

# Load store data
with open(r'\\192.168.100.5\config\.storage\energy_management_01KKCHQC1H76XNA33EYXJKFB4T', 'r', encoding='utf-8') as f:
    store = json.load(f)
store_data = store.get("data", {})

from custom_components.energy_management.sensor import EnergyProfileManager
from custom_components.energy_management.sensor import InverterOperationModeSensor

print("Mocks set up successfully. Instantiating EnergyProfileManager...")

class TestManager(EnergyProfileManager):
    def __init__(self, entry, hass=None):
        self.entry = entry
        self.hass = hass
        self.data = store_data
        self.store = types.ModuleType("mock_store")
        self.store.async_save = lambda d: None
        
        self.battery_soc_sensor = "sensor.inverter_battery"
        self.battery_capacity_sensor = "sensor.inverter_battery_capacity"
        self.forecast_today_sensor = "sensor.forecast_today"
        self.forecast_tomorrow_sensor = "sensor.forecast_tomorrow"
        self.forecast_today_hourly_sensor = "sensor.forecast_today_hourly"
        
        self.manual_mode_overrides = store_data.get("manual_mode_overrides")
        if self.manual_mode_overrides is None:
            self.manual_mode_overrides = {}
        self.hourly_manual_overrides = store_data.get("hourly_manual_overrides", {})
        
        self.last_blended_coeff = 1.0
        self.current_inverter_mode = "sale_pv"
        self.heuristic_hourly_data = {}
        self.dp_hourly_data = {}
        
    def get_setting(self, name, default=None): return self.data.get("settings", {}).get(name, default)
    def get_battery_state(self, soc_default=0.0): return 50.0, 17.0, 8.5
    def get_sensor_float(self, name, default=0.0): return float(self.data.get("sensor_last_values", {}).get(name, default or 0.0) or 0.0)
    def get_forecast_hourly_distribution(self, sensor, today_str): return {}
    def register_listener(self, func): pass

entry = types.ModuleType("entry")
entry.entry_id = "01KKCHQC1H76XNA33EYXJKFB4T"
entry.data = {"name": "Energy Management"}

manager = TestManager(entry)
sensor = InverterOperationModeSensor(manager, "Inverter Mode")

async def run_test():
    print("Triggering global plan update...")
    try:
        await manager.async_update_global_plan(force_strategy_recalc=True)
        print("Global plan updated successfully. Getting extra_state_attributes...")
        attrs = sensor.extra_state_attributes
        print("Success! Got attributes:")
        print(attrs.keys())
    except Exception as e:
        print("EXCEPTION RAISED:")
        traceback.print_exc()

import asyncio
asyncio.run(run_test())
