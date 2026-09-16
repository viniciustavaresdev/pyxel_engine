from __future__ import annotations

from dataclasses import dataclass

from engine.math.vector2d import Vector2D
from engine.scene.body import Body


@dataclass(frozen=True, slots=True)
class RaycastHit:
    """O que um raio acertou primeiro, e onde.

    Um valor, como o Rect: nasce pronto na resposta do `raycast` e nao
    muda. `body` e `None` quando o acerto foi em PAREDE -- e a unica
    distincao que a semana 3 precisa, porque uma bala que acerta parede
    some e uma que acerta corpo mata.

    `normal` aponta para FORA da superficie atingida, para o lado de
    onde o raio veio: `(-1, 0)` e a face esquerda de uma parede a
    direita. Sai de graca do percurso pela grade -- e o eixo que
    acabou de avancar --, e e o que um ricochete ou um decalque de
    sangue na parede vai querer. Zero quando o raio NASCEU dentro do
    solido: nao ha face para nomear, e inventar uma seria mentir.

    `distance` esta em unidades de mundo, sempre: a direcao e
    normalizada antes do percurso, entao passar um vetor de tamanho 3
    nao encurta o raio em tres vezes.
    """

    point: Vector2D
    normal: Vector2D
    distance: float
    body: Body | None
