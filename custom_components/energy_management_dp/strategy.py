import logging
from .strategy_base import StrategyEngine as StrategyEngineBase

_LOGGER = logging.getLogger(__name__)

class StrategyEngine(StrategyEngineBase):
    """
    Базовый движок стратегии. Специализированные модули эвристики (StrategyBuy, StrategySell) полностью удалены.
    """
    
    def __init__(self, manager):
        super().__init__(manager)

    def clear_cache(self):
        """Очистка кэша базового движка."""
        super().clear_cache()
    
    def get_market_strategy(self, mode="buy", allow_recalc=True):
        """Заглушка, возвращающая пустой словарь, так как эвристики отключены."""
        return {}
