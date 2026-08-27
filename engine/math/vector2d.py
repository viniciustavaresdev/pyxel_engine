from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Vector2D:
    """Ponto ou deslocamento no plano. Imutavel.

    Todo metodo devolve um vetor NOVO; nenhum altera o que recebeu.
    Isso e uma escolha de projeto, nao um detalhe: um vetor mutavel
    compartilhado e a fonte silenciosa de bugs onde mover um objeto
    move outro. Com `a.transform.position = b.transform.position` os
    dois nos passavam a apontar para o MESMO vetor, e daquele instante
    em diante andavam juntos -- sem erro, sem aviso, e sem nenhum teste
    que pegasse, porque ninguem escreve essa linha de proposito.

    Tres consequencias de graca:

    - nao existe `copy()`, porque nao ha o que copiar de um valor;
    - guardar um vetor recebido e seguro, sem cerimonia de defesa;
    - o vetor e hashavel, entao serve de chave de dicionario e de
      membro de conjunto.

    E uma quarta, que e a que interessa mais adiante: escrever em uma
    posicao passa obrigatoriamente por `transform.position = ...`, e
    uma atribuicao E interceptavel. Enquanto `position.x += 1` era
    valido, nenhum cache de transform mundial podia saber que ficou
    velho.
    """

    x: float = 0.0
    y: float = 0.0

    def __add__(self, other: Vector2D) -> Vector2D:
        return Vector2D(
            self.x + other.x,
            self.y + other.y,
        )

    def __sub__(self, other: Vector2D) -> Vector2D:
        return Vector2D(
            self.x - other.x,
            self.y - other.y,
        )

    def __mul__(self, scalar: float) -> Vector2D:
        return Vector2D(
            self.x * scalar,
            self.y * scalar,
        )

    def __rmul__(self, scalar: float) -> Vector2D:
        return self * scalar

    def __truediv__(self, scalar: float) -> Vector2D:
        if scalar == 0:
            raise ZeroDivisionError("Cannot divide a vector by zero.")

        return Vector2D(
            self.x / scalar,
            self.y / scalar,
        )

    def magnitude(self) -> float:
        return math.hypot(self.x, self.y)

    def normalized(self) -> Vector2D:
        magnitude = self.magnitude()

        if magnitude == 0:
            return Vector2D()

        return self / magnitude

    def rotated(self, radians: float) -> Vector2D:
        # Sentido anti-horario no plano matematico. Como o Y da tela
        # cresce para baixo, na pratica o giro aparece horario -- o que
        # e a convencao de todo engine 2D com origem no topo-esquerdo.
        cos = math.cos(radians)
        sin = math.sin(radians)

        return Vector2D(
            self.x * cos - self.y * sin,
            self.x * sin + self.y * cos,
        )

    def scaled(self, factors: Vector2D) -> Vector2D:
        # Componente a componente, diferente de `* escalar`. Metodo
        # nomeado em vez de sobrecarga do __mul__ para que a diferenca
        # entre escalar e vetor fique visivel na chamada.
        return Vector2D(
            self.x * factors.x,
            self.y * factors.y,
        )

    def dot(self, other: Vector2D) -> float:
        return self.x * other.x + self.y * other.y

    def distance_to(self, other: Vector2D) -> float:
        return (self - other).magnitude()
