from abc import ABC, abstractmethod

from engine.math.rect import Rect
from engine.math.vector2d import Vector2D


class Renderer(ABC):
    """Porta de desenho.

    Fala em Vector2D e Rect, nao em floats soltos, pelo mesmo motivo
    que o resto da engine: `get_world_position()` devolve um Vector2D,
    e desmonta-lo em `.x, .y` em cada on_render espalharia por todo no
    de jogo um trabalho que pertence ao adaptador. Quem desmonta para o
    backend e quem conhece o backend.

    O ganho colateral e de tipo: `x, y, u, v, width, height` eram seis
    floats intercambiaveis, e trocar dois deles era um bug que nenhum
    type checker pegava. Agrupados, a troca nao compila.
    """

    @abstractmethod
    def clear(self, color: int = 0) -> None:
        pass

    @abstractmethod
    def draw_rect(
        self,
        position: Vector2D,
        size: Vector2D,
        color: int,
    ) -> None:
        pass

    @abstractmethod
    def draw_sprite(
        self,
        center: Vector2D,
        image: int,
        region: Rect,
        color_key: int | None = None,
        rotation: float = 0.0,
        scale: float = 1.0,
    ) -> None:
        """Copia `region` do banco `image` centrada em `center`.

        `center`, e nao o canto, porque este e o unico metodo da porta
        que gira -- e um desenho que gira precisa dizer EM TORNO DE QUE.
        O ponto passado aqui e ao mesmo tempo o centro do sprite e o
        eixo da rotacao e da escala. Nomear o parametro de `position`
        deixaria a duvida entre canto e centro justamente onde ela
        importa; `draw_rect`, que nao gira, continua falando em canto
        porque para ele nao ha ambiguidade.

        Quem tem um anchor diferente de CENTER converte antes de
        chamar: `VisualNode.get_world_center()` faz exatamente isso.

        `rotation` em RADIANOS, para casar com Transform.rotation -- o
        adaptador converte para a unidade do backend.

        `scale` e um float, nao um Vector2D: e uma limitacao real do
        Pyxel, cujo blt so faz escala uniforme. Aceitar um Vector2D
        aqui prometeria escala nao-uniforme que o backend nao entrega.

        `color_key` e a cor tratada como transparente; None desenha
        opaco. Largura ou altura negativa em `region` espelha o sprite:
        e assim que se vira um personagem sem uma segunda arte.
        """

    @abstractmethod
    def draw_text(
        self,
        position: Vector2D,
        text: str,
        color: int,
    ) -> None:
        pass

    @abstractmethod
    def set_camera(self, offset: Vector2D) -> None:
        """Move a janela de visao para `offset`, em coordenadas de mundo.

        Tudo que for desenhado depois disto sai deslocado. E o que
        permite uma cena maior que a tela sem que cada no precise
        subtrair a posicao da camera por conta propria.
        """

    @abstractmethod
    def reset_camera(self) -> None:
        """Volta a desenhar em coordenadas de tela.

        Necessario para HUD: vida e pontuacao nao podem rolar junto com
        o cenario.
        """
