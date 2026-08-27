from abc import ABC, abstractmethod

from engine.input.key import Key


class Input(ABC):
    """Estado do teclado no frame atual.

    Tres perguntas distintas, porque jogos precisam das tres: segurar
    para andar, o instante do pulo, e o instante de soltar (carregar um
    tiro). Colapsar isso em `is_pressed` faria o pulo disparar em todo
    frame em que a tecla estivesse baixa.
    """

    @abstractmethod
    def is_pressed(self, key: Key) -> bool:
        """A tecla esta baixa agora (em qualquer frame)."""

    @abstractmethod
    def is_just_pressed(self, key: Key) -> bool:
        """A tecla desceu NESTE frame."""

    @abstractmethod
    def is_just_released(self, key: Key) -> bool:
        """A tecla subiu NESTE frame."""
