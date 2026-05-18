import sys
from unittest.mock import MagicMock

class MockBase(object):
    pass

sys.modules['homeassistant'] = MagicMock()
sys.modules['homeassistant.components'] = MagicMock()

# Define dummy SensorEntity and RestoreEntity classes
class DummySensorEntity(object):
    pass

class DummyRestoreEntity(object):
    pass

# We create custom mock modules with real classes inside
import types
sensor_mod = types.ModuleType('homeassistant.components.sensor')
sensor_mod.SensorEntity = DummySensorEntity
sensor_mod.SensorStateClass = MagicMock()
sensor_mod.SensorDeviceClass = MagicMock()
sys.modules['homeassistant.components.sensor'] = sensor_mod

restore_mod = types.ModuleType('homeassistant.helpers.restore_state')
restore_mod.RestoreEntity = DummyRestoreEntity
sys.modules['homeassistant.helpers.restore_state'] = restore_mod

sys.modules['homeassistant.components.http'] = MagicMock()
sys.modules['homeassistant.loader'] = MagicMock()
sys.modules['homeassistant.helpers'] = MagicMock()
sys.modules['homeassistant.helpers.event'] = MagicMock()
sys.modules['homeassistant.helpers.device_registry'] = MagicMock()
sys.modules['homeassistant.core'] = MagicMock()
sys.modules['homeassistant.config_entries'] = MagicMock()
sys.modules['homeassistant.const'] = MagicMock()
sys.modules['homeassistant.helpers.storage'] = MagicMock()
sys.modules['homeassistant.util'] = MagicMock()

import datetime
class MockDt:
    @staticmethod
    def now():
        return datetime.datetime.now()
    @staticmethod
    def as_local(d):
        return d
sys.modules['homeassistant.util'].dt = MockDt

# Also mock strategy classes that might be imported
sys.modules['.strategy_base'] = MagicMock()
sys.modules['.strategy_buy'] = MagicMock()
sys.modules['.strategy_sell'] = MagicMock()
sys.modules['.strategy_dp'] = MagicMock()
sys.modules['.utils'] = MagicMock()
sys.modules['.dispatch_plan'] = MagicMock()
sys.modules['.const'] = MagicMock()
