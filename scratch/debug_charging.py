import sys
sys.stdout.reconfigure(encoding='utf-8')

import logging
logging.basicConfig(level=logging.ERROR)

import types
import datetime
import importlib.machinery
import json
import os
import traceback

# Setup mock modules
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
class MockStore:
    def __init__(self, hass, version, key):
        self.key = key
    async def async_load(self):
        with open(r'\\192.168.100.5\config\.storage\energy_management_01KKCHQC1H76XNA33EYXJKFB4T', 'r', encoding='utf-8') as f:
            store = json.load(f)
        return store.get("data", {})
    async def async_save(self, data):
        pass
storage_mod.Store = MockStore
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
mock_dt.now = lambda: datetime.datetime.now(datetime.timezone.utc)
mock_dt.utcnow = lambda: datetime.datetime.now(datetime.timezone.utc)
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
                return None
            m = types.ModuleType(fullname)
            m.__path__ = []
            sys.modules[fullname] = m
            return importlib.machinery.ModuleSpec(fullname, DummyLoader())
        return None
sys.meta_path.insert(0, MockFinder())

sys.path.append(os.path.abspath('.'))
sys.path.append(os.path.abspath('./custom_components'))

# Load entry config
with open(r'\\192.168.100.5\config\.storage\core.config_entries', 'r', encoding='utf-8') as f:
    entries = json.load(f)
entry_data = next(ent for ent in entries["data"]["entries"] if ent.get("domain") == "energy_management_dp")

class MockConfigEntry:
    def __init__(self, entry_dict):
        self.entry_id = entry_dict["entry_id"]
        self.data = entry_dict["data"]
        self.options = entry_dict.get("options", {})
        self.title = entry_dict["title"]
config_entry = MockConfigEntry(entry_data)

class MockState:
    def __init__(self, state_str, attributes=None):
        self.state = state_str
        self.attributes = attributes or {}
class MockStates:
    def __init__(self):
        # Let's mock the actual entities we need for get_battery_state
        self.states_map = {
            entry_data["data"].get("battery_soc_sensor", "sensor.battery_state_of_charge"): MockState("39.0"),
            entry_data["data"].get("battery_capacity_sensor", "sensor.battery_capacity"): MockState("17.0"),
        }
    def get(self, entity_id):
        return self.states_map.get(entity_id)

class MockHass:
    def __init__(self):
        self.states = MockStates()
    def async_create_task(self, coro): pass
    def async_add_executor_job(self, func, *args): return func(*args)

from custom_components.energy_management_dp.sensor import EnergyProfileManager
from custom_components.energy_management_dp.strategy import StrategyEngine

async def run():
    hass = MockHass()
    manager = EnergyProfileManager(hass, config_entry)
    await manager.async_load()
    
    # Run strategy engine simulation
    # Let's simulate for 24 hours starting now (local time 09:44)
    now = datetime.datetime.now()
    sim_hours = list(range(now.hour, now.hour + 24))
    
    engine = StrategyEngine(manager)
    
    # Trace 1: Normal mode (no overrides)
    overrides_none = {}
    _, history_none, _ = engine.run_soc_simulation(
        start_soc=39.0,
        sim_range=sim_hours,
        now=now,
        mode_overrides=overrides_none
    )
    
    # Trace 2: Charge override at 11:00
    # Find absolute hour index of 11:00
    target_abs_hour = now.hour
    for h in sim_hours:
        if (h % 24) == 11:
            target_abs_hour = h
            break
            
    # Set the override to buy mode
    manager.hourly_manual_overrides[datetime.datetime(now.year, now.month, now.day, 11).strftime("%Y-%m-%d 11:00")] = {
        "mode": "buy",
        "soc_limit": 100.0,
        "power": 6.6,
        "amps": 128.8
    }
    
    _, history_charge, _ = engine.run_soc_simulation(
        start_soc=39.0,
        sim_range=sim_hours,
        now=now,
        mode_overrides={}
    )
    
    print("\nHOUR 11 NORMAL:")
    print(json.dumps(history_none.get(11), indent=2))
    
    print("\nHOUR 11 OVERRIDE CHARGE:")
    print(json.dumps(history_charge.get(11), indent=2))

import asyncio
asyncio.run(run())
