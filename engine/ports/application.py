from abc import ABC, abstractmethod
from collections.abc import Callable

from engine.runtime.application_config import ApplicationConfig


class Application(ABC):

    @abstractmethod
    def initialize(
        self,
        config: ApplicationConfig,
    ) -> None:
        pass

    @abstractmethod
    def run(
        self,
        update: Callable[[], None],
        render: Callable[[], None],
    ) -> None:
        pass

    @abstractmethod
    def quit(self) -> None:
        # Encerra o loop iniciado por run(). Sem isto, parar a Engine
        # apenas congelaria a janela: update e render virariam no-op e
        # o backend seguiria girando sobre uma tela morta.
        pass
