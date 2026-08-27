from abc import ABC, abstractmethod


class TimeProvider(ABC):

    @abstractmethod
    def now(self) -> float:
        pass
