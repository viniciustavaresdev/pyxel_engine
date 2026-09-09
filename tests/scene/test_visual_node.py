import math

import pytest

from engine.math.anchor import Anchor
from engine.math.rect import Rect
from engine.math.transform import Transform
from engine.math.vector2d import Vector2D
from engine.scene.node import Node
from engine.scene.visual_node import VisualNode


class CountingNode(VisualNode):
    """Conta quantas vezes a PROPRIA transform mundial foi resolvida.

    Nao conta as dos ancestrais: cada no da cadeia tem o proprio
    contador, o que permite afirmar tanto "este metodo resolveu uma vez
    so" quanto "a cadeia inteira foi subida uma vez so".
    """

    def __init__(
        self,
        name: str | None = None,
        size: Vector2D | None = None,
        anchor: Anchor = Anchor.CENTER,
    ) -> None:
        super().__init__(name, size, anchor)

        self.resolutions = 0

    def get_world_transform(self) -> Transform:
        self.resolutions += 1

        return super().get_world_transform()


class TestDefaults:
    def test_defaults_to_the_center_anchor(self):
        # O default que faz a rotacao girar em torno do centro sem que
        # o jogo precise dizer nada.
        assert VisualNode().anchor == Anchor.CENTER

    def test_starts_without_size(self):
        assert VisualNode().size == Vector2D(0.0, 0.0)

    def test_resizing_one_node_leaves_the_other_alone(self):
        # Dois nos sem tamanho compartilham a mesma instancia de (0, 0)
        # -- e agora isso e inofensivo, porque redimensionar e trocar o
        # valor inteiro, nao escrever dentro dele.
        a = VisualNode()
        b = VisualNode()

        a.size = Vector2D(99.0, 99.0)

        assert b.size == Vector2D(0.0, 0.0)


class TestCenteredAnchor:
    def test_the_origin_is_the_center(self):
        node = VisualNode(size=Vector2D(8.0, 8.0))
        node.transform.position = Vector2D(100.0, 50.0)

        assert node.get_world_center() == Vector2D(100.0, 50.0)

    def test_the_box_is_drawn_half_a_size_back(self):
        node = VisualNode(size=Vector2D(8.0, 8.0))
        node.transform.position = Vector2D(100.0, 50.0)

        assert node.get_world_top_left() == Vector2D(96.0, 46.0)

    def test_rotating_does_not_move_the_center(self):
        # O ponto do exercicio inteiro: girar em torno do centro
        # significa que o centro fica onde estava.
        node = VisualNode(size=Vector2D(8.0, 8.0))
        node.transform.position = Vector2D(100.0, 50.0)

        node.transform.rotation = math.pi / 3.0

        assert node.get_world_center() == Vector2D(100.0, 50.0)


class TestOtherAnchors:
    def test_top_left_anchor_draws_from_the_origin(self):
        # A convencao antiga, agora explicita em vez de acidental.
        node = VisualNode(size=Vector2D(8.0, 8.0), anchor=Anchor.TOP_LEFT)
        node.transform.position = Vector2D(100.0, 50.0)

        assert node.get_world_top_left() == Vector2D(100.0, 50.0)

    def test_top_left_anchor_puts_the_center_half_a_box_away(self):
        node = VisualNode(size=Vector2D(8.0, 8.0), anchor=Anchor.TOP_LEFT)
        node.transform.position = Vector2D(100.0, 50.0)

        assert node.get_world_center() == Vector2D(104.0, 54.0)

    def test_bottom_center_anchor_keeps_the_origin_at_the_feet(self):
        node = VisualNode(
            size=Vector2D(8.0, 16.0), anchor=Anchor.BOTTOM_CENTER
        )
        node.transform.position = Vector2D(100.0, 50.0)

        assert node.get_world_top_left() == Vector2D(96.0, 34.0)

    def test_a_taller_sprite_grows_upward_from_the_feet(self):
        # O que o anchor de pes compra: trocar a arte por uma mais alta
        # nao afunda o personagem no chao.
        short = VisualNode(
            size=Vector2D(8.0, 16.0), anchor=Anchor.BOTTOM_CENTER
        )
        tall = VisualNode(
            size=Vector2D(8.0, 24.0), anchor=Anchor.BOTTOM_CENTER
        )

        for node in (short, tall):
            node.transform.position = Vector2D(100.0, 50.0)

        bottom_of_short = short.get_world_top_left().y + short.size.y
        bottom_of_tall = tall.get_world_top_left().y + tall.size.y

        assert bottom_of_short == bottom_of_tall == 50.0


class TestScale:
    def test_the_size_follows_the_scale(self):
        node = VisualNode(size=Vector2D(8.0, 8.0))
        node.transform.scale = Vector2D(2.0, 3.0)

        assert node.get_world_size() == Vector2D(16.0, 24.0)

    def test_scaling_a_centered_node_grows_around_the_center(self):
        node = VisualNode(size=Vector2D(8.0, 8.0))
        node.transform.position = Vector2D(100.0, 50.0)
        node.transform.scale = Vector2D(2.0, 2.0)

        assert node.get_world_center() == Vector2D(100.0, 50.0)
        assert node.get_world_top_left() == Vector2D(92.0, 42.0)

    def test_scaling_a_top_left_node_grows_to_the_right_and_down(self):
        node = VisualNode(size=Vector2D(8.0, 8.0), anchor=Anchor.TOP_LEFT)
        node.transform.position = Vector2D(100.0, 50.0)
        node.transform.scale = Vector2D(2.0, 2.0)

        assert node.get_world_top_left() == Vector2D(100.0, 50.0)

    def test_the_parent_scale_reaches_the_child_box(self):
        parent = Node("Parent")
        parent.transform.scale = Vector2D(2.0, 2.0)
        child = VisualNode("Child", size=Vector2D(8.0, 8.0))
        parent.add_child(child)

        assert child.get_world_size() == Vector2D(16.0, 16.0)


class TestHierarchy:
    def test_a_child_orbits_the_center_of_the_parent(self):
        # O sintoma que motivou o anchor: com a origem no canto, o
        # satelite orbitava o canto superior esquerdo do jogador.
        player = VisualNode("Player", size=Vector2D(8.0, 8.0))
        player.transform.position = Vector2D(100.0, 50.0)

        satellite = VisualNode("Satellite", size=Vector2D(2.0, 2.0))
        satellite.transform.position = Vector2D(20.0, 0.0)
        player.add_child(satellite)

        player.transform.rotation = math.pi

        center = satellite.get_world_center()

        assert center.x == pytest.approx(80.0)
        assert center.y == pytest.approx(50.0, abs=1e-9)

    def test_the_orbit_radius_is_measured_from_center_to_center(self):
        player = VisualNode("Player", size=Vector2D(8.0, 8.0))
        player.transform.position = Vector2D(100.0, 50.0)

        satellite = VisualNode("Satellite", size=Vector2D(2.0, 2.0))
        satellite.transform.position = Vector2D(20.0, 0.0)
        player.add_child(satellite)

        for eighth in range(8):
            player.transform.rotation = eighth * math.pi / 4.0

            distance = satellite.get_world_center().distance_to(
                player.get_world_center()
            )

            assert distance == pytest.approx(20.0)

    def test_a_rotating_parent_carries_the_child_box_along(self):
        parent = VisualNode("Parent", size=Vector2D(8.0, 8.0))
        parent.transform.position = Vector2D(0.0, 0.0)
        parent.transform.rotation = math.pi / 2.0

        child = VisualNode("Child", size=Vector2D(4.0, 4.0))
        child.transform.position = Vector2D(10.0, 0.0)
        parent.add_child(child)

        top_left = child.get_world_top_left()

        assert top_left.x == pytest.approx(-2.0, abs=1e-9)
        assert top_left.y == pytest.approx(8.0)


class TestWorldBounds:
    def test_the_bounds_are_the_corner_and_the_size(self):
        node = VisualNode(size=Vector2D(8.0, 8.0))
        node.transform.position = Vector2D(100.0, 50.0)

        assert node.get_world_bounds() == Rect(96.0, 46.0, 8.0, 8.0)

    def test_the_bounds_center_is_the_world_center(self):
        node = VisualNode(size=Vector2D(8.0, 16.0), anchor=Anchor.TOP_LEFT)
        node.transform.position = Vector2D(100.0, 50.0)

        assert node.get_world_bounds().center == node.get_world_center()

    def test_the_bounds_agree_with_the_two_older_methods(self):
        # A peca nova nao pode discordar das antigas: e a mesma caixa
        # dita de uma vez so.
        for anchor in (Anchor.TOP_LEFT, Anchor.CENTER, Anchor.BOTTOM_CENTER):
            node = VisualNode(size=Vector2D(8.0, 16.0), anchor=anchor)
            node.transform.position = Vector2D(100.0, 50.0)
            node.transform.rotation = math.pi / 5.0
            node.transform.scale = Vector2D(2.0, 3.0)

            bounds = node.get_world_bounds()

            assert bounds.position == node.get_world_top_left()
            assert bounds.size == node.get_world_size()

    def test_the_scale_reaches_the_bounds(self):
        node = VisualNode(size=Vector2D(8.0, 8.0))
        node.transform.position = Vector2D(100.0, 50.0)
        node.transform.scale = Vector2D(2.0, 2.0)

        assert node.get_world_bounds() == Rect(92.0, 42.0, 16.0, 16.0)

    def test_the_hierarchy_reaches_the_bounds(self):
        parent = Node("Parent")
        parent.transform.position = Vector2D(100.0, 50.0)
        parent.transform.scale = Vector2D(2.0, 2.0)

        child = CountingNode("Child", size=Vector2D(4.0, 4.0))
        child.transform.position = Vector2D(10.0, 0.0)
        parent.add_child(child)

        assert child.get_world_bounds() == Rect(116.0, 46.0, 8.0, 8.0)

    def test_rotating_moves_the_box_but_never_tilts_it(self):
        # A perda assumida: a caixa e sempre alinhada aos eixos, entao
        # girar 90 graus um retangulo alto NAO o deixa deitado.
        node = VisualNode(
            size=Vector2D(8.0, 16.0), anchor=Anchor.BOTTOM_CENTER
        )
        node.transform.position = Vector2D(100.0, 50.0)
        node.transform.rotation = math.pi / 2.0

        bounds = node.get_world_bounds()

        assert bounds.size == Vector2D(8.0, 16.0)
        assert bounds.center.x == pytest.approx(108.0)
        assert bounds.center.y == pytest.approx(50.0, abs=1e-9)


class TestBoundsCollision:
    # O outro lado da mesma peca: o que get_world_bounds entrega de
    # graca por devolver um Rect em vez de dois vetores.

    def test_two_overlapping_nodes_report_a_hit(self):
        a = VisualNode(size=Vector2D(8.0, 8.0))
        a.transform.position = Vector2D(0.0, 0.0)

        b = VisualNode(size=Vector2D(8.0, 8.0))
        b.transform.position = Vector2D(4.0, 0.0)

        assert a.get_world_bounds().intersects(b.get_world_bounds())

    def test_nodes_a_size_apart_do_not_touch(self):
        a = VisualNode(size=Vector2D(8.0, 8.0))
        a.transform.position = Vector2D(0.0, 0.0)

        b = VisualNode(size=Vector2D(8.0, 8.0))
        b.transform.position = Vector2D(8.0, 0.0)

        assert not a.get_world_bounds().intersects(b.get_world_bounds())

    def test_a_click_lands_on_the_node_under_it(self):
        node = VisualNode(size=Vector2D(8.0, 8.0), anchor=Anchor.TOP_LEFT)
        node.transform.position = Vector2D(20.0, 20.0)

        assert node.get_world_bounds().contains(Vector2D(24.0, 24.0))
        assert not node.get_world_bounds().contains(Vector2D(19.0, 24.0))


class TestChainClimbs:
    """Trava o motivo de get_world_bounds existir.

    Sem estes testes a peca continuaria correta e voltaria a ser cara
    na primeira vez que alguem a reescrevesse em termos dos metodos
    antigos -- e nenhum teste de valor perceberia.
    """

    def test_bounds_resolve_the_world_transform_once(self):
        node = CountingNode(size=Vector2D(8.0, 8.0))

        node.get_world_bounds()

        assert node.resolutions == 1

    def test_top_left_no_longer_pays_twice(self):
        # Custava duas: uma pelo centro e outra pelo tamanho.
        node = CountingNode(size=Vector2D(8.0, 8.0))

        node.get_world_top_left()

        assert node.resolutions == 1

    def test_the_whole_chain_is_climbed_once_per_bounds(self):
        # O custo cresce com a profundidade -- e o que o cache do passo
        # seguinte ataca -- mas nao pode crescer com o numero de valores
        # que o no pede da propria caixa.
        root = CountingNode("0", size=Vector2D(8.0, 8.0))
        chain = [root]

        for i in range(1, 4):
            node = CountingNode(str(i), size=Vector2D(8.0, 8.0))
            chain[-1].add_child(node)
            chain.append(node)

        chain[-1].get_world_bounds()

        assert [node.resolutions for node in chain] == [1, 1, 1, 1]

    def test_the_old_idiom_cost_three_climbs(self):
        # A medida do antes, escrita para que o ganho fique registrado
        # em teste e nao so no README.
        node = CountingNode(size=Vector2D(8.0, 8.0))

        node.get_world_center()
        node.get_world_top_left()
        node.get_world_size()

        assert node.resolutions == 3


class TestRotationWithAnOffCenterAnchor:
    def test_the_box_swings_around_the_origin(self):
        # Com o anchor nos pes, girar o no faz o corpo balancar em
        # torno dos pes -- que e exatamente o que se quer de um
        # personagem tombando, e o oposto do que se quer de uma nave.
        node = VisualNode(
            size=Vector2D(8.0, 16.0), anchor=Anchor.BOTTOM_CENTER
        )
        node.transform.position = Vector2D(100.0, 50.0)
        node.transform.rotation = math.pi / 2.0

        center = node.get_world_center()

        assert center.x == pytest.approx(108.0)
        assert center.y == pytest.approx(50.0, abs=1e-9)

    def test_scale_is_applied_before_rotation(self):
        # Mesma ordem do Transform.compose. Se a rotacao viesse antes, o
        # deslocamento seria esticado no eixo ja girado.
        node = VisualNode(
            size=Vector2D(8.0, 16.0), anchor=Anchor.BOTTOM_CENTER
        )
        node.transform.position = Vector2D(0.0, 0.0)
        node.transform.scale = Vector2D(1.0, 3.0)
        node.transform.rotation = math.pi / 2.0

        center = node.get_world_center()

        assert center.x == pytest.approx(24.0)
        assert center.y == pytest.approx(0.0, abs=1e-9)
