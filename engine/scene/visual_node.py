from __future__ import annotations

from engine.math.anchor import Anchor
from engine.math.rect import Rect
from engine.math.transform import Transform
from engine.math.vector2d import Vector2D
from engine.scene.node import Node


class VisualNode(Node):
    """No que ocupa espaco na tela: tem tamanho e um anchor.

    Node nao tem tamanho de proposito -- uma Camera, um ponto de spawn
    ou um no que existe so para agrupar filhos nao tem caixa nenhuma, e
    dar um `size` a todos eles seria mentir sobre o que a arvore
    contem. Quem desenha tem caixa, e e aqui que ela entra.

    E aqui, tambem, que mora a resposta para "girar em torno do centro".
    A rotacao SEMPRE acontece na origem do no; o que muda e onde a
    origem cai dentro do desenho, e quem decide isso e o `anchor`. Com
    o default Anchor.CENTER a origem fica no centro da caixa, entao:

      - o proprio no gira em torno do centro;
      - um filho pendurado nele orbita esse centro;
      - a camera presa a ele enquadra esse centro.

    Tudo isso sem tocar em Transform, que continua sendo so um sistema
    de coordenadas -- posicao, rotacao e escala, nada de pixels.
    """

    def __init__(
        self,
        name: str | None = None,
        size: Vector2D | None = None,
        anchor: Anchor = Anchor.CENTER,
    ) -> None:
        super().__init__(name)

        # size default_factory pelo mesmo motivo do Transform: um
        # Vector2D mutavel como default literal seria compartilhado por
        # todos os nos criados sem argumento.
        self.size = size if size is not None else Vector2D()
        self.anchor = anchor

    def get_world_size(self) -> Vector2D:
        """Tamanho ja esticado pela escala acumulada da hierarquia."""
        return self.size.scaled(self.get_world_transform().scale)

    def get_world_center(self) -> Vector2D:
        """Centro da caixa, em coordenadas de mundo.

        Exato para qualquer anchor e qualquer rotacao: o deslocamento
        ate o centro e primeiro esticado pela escala e so entao girado,
        na mesma ordem que Transform.compose usa. E o ponto que os
        backends que giram em torno do centro -- o blt do Pyxel -- e a
        deteccao de colisao circular vao querer.
        """
        world = self.get_world_transform()

        return self._center_of(world, self.size.scaled(world.scale))

    def get_world_bounds(self) -> Rect:
        """Caixa alinhada aos eixos, no mundo, com UMA subida de cadeia.

        E o metodo que o on_render deve usar. O idioma anterior --
        `draw_rect(get_world_top_left(), get_world_size(), cor)` --
        parecia barato e custava tres resolucoes da transform mundial
        por no, cada uma subindo a hierarquia inteira e alocando um
        Transform e varios vetores por nivel. Aqui a transform e
        resolvida uma vez e os dois valores saem dela.

        Devolver um Rect, e nao uma tupla de dois vetores, e o que faz
        esta peca servir tambem de colisao: `bounds.intersects(outro)`
        ja e AABB, sem uma linha nova.

        Mesma perda assumida do `get_world_top_left`: a caixa e
        ALINHADA AOS EIXOS. O centro respeita a rotacao da hierarquia
        inteira, a orientacao nao sobrevive.
        """
        world = self.get_world_transform()
        size = self.size.scaled(world.scale)

        return Rect.from_center_size(self._center_of(world, size), size)

    def get_world_top_left(self) -> Vector2D:
        """Canto superior esquerdo da caixa ALINHADA AOS EIXOS.

        Para primitivas que nao sabem girar -- draw_rect, texto, uma
        caixa de debug. O centro respeita a rotacao da hierarquia
        inteira (um filho de um pai girando orbita de verdade), mas a
        ORIENTACAO da caixa e perdida, porque um retangulo alinhado aos
        eixos nao tem como expressa-la.

        A perda e assumida, e nao um bug escondido: e melhor um quadrado
        que fica parado enquanto gira do que um quadrado cujo canto
        bambeia em volta do lugar certo.

        Quem tambem precisa do tamanho -- todo on_render -- deve chamar
        `get_world_bounds()` em vez deste mais o `get_world_size()`:
        sao duas subidas de cadeia contra uma.
        """
        return self.get_world_bounds().position

    def _center_of(self, world: Transform, size: Vector2D) -> Vector2D:
        # A conta do centro, isolada para que get_world_center e
        # get_world_bounds a compartilhem sem que nenhum dos dois
        # precise resolver a transform mundial duas vezes.
        return world.position + self.anchor.to_center(size).rotated(
            world.rotation
        )
