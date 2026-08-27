from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from engine.math.vector2d import Vector2D


@dataclass(frozen=True, slots=True)
class Anchor:
    """Ponto da caixa de um no que coincide com a origem dele.

    Em fracoes, nao em pixels: (0, 0) e o canto superior esquerdo da
    caixa, (1, 1) o inferior direito, (0.5, 0.5) o centro. Normalizado
    para nao depender do tamanho -- o mesmo Anchor.BOTTOM_CENTER serve
    para um sprite 8x8 e para um 32x48, e continua valendo quando a
    escala do no muda no meio do jogo.

    E este valor, e nao o Transform, que decide em torno de que ponto
    um no gira: a rotacao sempre acontece na origem, entao mudar o
    anchor e mudar onde a origem cai dentro do desenho.

    frozen pelo mesmo motivo do Rect: e um valor, e quase sempre uma
    constante compartilhada por muitos nos ao mesmo tempo.
    """

    x: float
    y: float

    TOP_LEFT: ClassVar[Anchor]
    TOP_CENTER: ClassVar[Anchor]
    TOP_RIGHT: ClassVar[Anchor]
    CENTER_LEFT: ClassVar[Anchor]
    CENTER: ClassVar[Anchor]
    CENTER_RIGHT: ClassVar[Anchor]
    BOTTOM_LEFT: ClassVar[Anchor]
    BOTTOM_CENTER: ClassVar[Anchor]
    BOTTOM_RIGHT: ClassVar[Anchor]

    def point_in(self, size: Vector2D) -> Vector2D:
        """Onde o anchor cai dentro de uma caixa deste tamanho.

        Medido a partir do canto superior esquerdo da caixa. Como a
        origem do no fica exatamente sobre esse ponto, o vetor daqui e
        tambem o quanto a caixa recua em relacao a origem -- com sinal
        trocado.
        """
        return Vector2D(self.x * size.x, self.y * size.y)

    def to_center(self, size: Vector2D) -> Vector2D:
        """Vetor que vai do anchor ate o centro da caixa.

        Existe porque alguns backends -- o blt do Pyxel entre eles --
        so sabem girar em torno do centro do que desenham. Este e o
        deslocamento que traduz "a origem esta AQUI" para "o centro do
        desenho esta ALI", que e o que esses backends pedem.

        Zero quando o anchor e CENTER, que e o caso comum.
        """
        return Vector2D(
            (0.5 - self.x) * size.x,
            (0.5 - self.y) * size.y,
        )


Anchor.TOP_LEFT = Anchor(0.0, 0.0)
Anchor.TOP_CENTER = Anchor(0.5, 0.0)
Anchor.TOP_RIGHT = Anchor(1.0, 0.0)
Anchor.CENTER_LEFT = Anchor(0.0, 0.5)
Anchor.CENTER = Anchor(0.5, 0.5)
Anchor.CENTER_RIGHT = Anchor(1.0, 0.5)
Anchor.BOTTOM_LEFT = Anchor(0.0, 1.0)
# O anchor de personagem: a origem nos pes faz o no encostar no chao
# sozinho, e faz um sprite mais alto crescer para cima em vez de
# afundar no cenario.
Anchor.BOTTOM_CENTER = Anchor(0.5, 1.0)
Anchor.BOTTOM_RIGHT = Anchor(1.0, 1.0)
