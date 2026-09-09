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

    # Tela <-> mundo
    #
    # As duas conversoes moram aqui porque o deslocamento e da camera.
    # Fora dela, cada no que precisasse do cursor refaria a subtracao
    # da meia tela na mao -- que e exatamente o que a camera existe
    # para evitar, e o mesmo argumento que ja pos o `get_view_offset`
    # neste arquivo.
    #
    # Sao TRANSLACAO PURA, e isso nao e simplificacao: e a inversa
    # exata do que o enquadramento faz. A porta `Renderer` enquadra com
    # `set_camera(offset)`, um deslocamento e nada mais -- entao uma
    # conversao que aplicasse rotacao ou zoom da camera discordaria do
    # que aparece na tela. Girar a camera nao gira a vista hoje, e a
    # conversao conta a mesma verdade que o desenho.
    #
    # Valem para a camada `world`. Na `ui` tela E mundo, e nenhuma das
    # duas deve ser chamada.

    def screen_to_world(self, screen: Vector2D) -> Vector2D:
        """Onde um ponto da TELA cai no mundo.

        E o caminho da mira: o ponteiro responde em coordenadas de
        tela, e o jogo precisa do alvo em mundo.

        Um ponto fora da tela converte sem reclamar -- o cursor sai
        pela borda, e recortar aqui seria a camera decidindo uma regra
        de jogo.
        """
        return screen + self.get_view_offset()

    def world_to_screen(self, world: Vector2D) -> Vector2D:
        """Onde um ponto do MUNDO aparece na tela.

        A inversa da de cima, e e assim que ela e testada. Serve a quem
        desenha em espaco de tela algo que segue um objeto do mundo:
        um marcador de inimigo fora do enquadramento, uma seta de
        objetivo, um nome de NPC.
        """
        return world - self.get_view_offset()
