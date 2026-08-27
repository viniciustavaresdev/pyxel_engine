from __future__ import annotations

from engine.math.vector2d import Vector2D
from engine.scene.node import Node


class Camera(Node):
    """Ponto de vista da cena, e um Node como qualquer outro.

    Ser um Node e o ponto: pendure a Camera como filha do jogador e ela
    o segue de graca pela transform hierarquica, sem uma linha de
    codigo de "follow".

    A posicao MUNDIAL da camera e o CENTRO da tela, nao o canto. Isso
    inverte o sinal em relacao ao backend (que pensa em canto superior
    esquerdo), mas e o que casa com a intuicao de "a camera esta em
    cima do jogador" -- e evita que todo jogo repita a mesma subtracao
    de meia tela.
    """

    def __init__(
        self,
        name: str | None = None,
        viewport_width: float = 0.0,
        viewport_height: float = 0.0,
    ) -> None:
        super().__init__(name)

        self.viewport_width = viewport_width
        self.viewport_height = viewport_height

    def get_view_offset(self) -> Vector2D:
        """Canto superior esquerdo da visao, em coordenadas de mundo.

        Com viewport zerado o resultado e a propria posicao da camera,
        ou seja, a semantica vira "canto" -- util para uma camera presa
        a uma grade de tiles.
        """
        center = self.get_world_position()

        return center - Vector2D(
            self.viewport_width / 2.0,
            self.viewport_height / 2.0,
        )
