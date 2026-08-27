# engine/infrastructure/time/performance_time_provider.py

import time

from engine.ports.time_provider import TimeProvider


class PerformanceTimeProvider(TimeProvider):

    def now(self) -> float:
        return time.perf_counter()
