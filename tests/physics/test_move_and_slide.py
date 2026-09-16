"""Collision.move_and_slide: caixas contra a grade, um eixo de cada vez.

Cada teste DESENHA o cenario com `SpyTileSource.from_rows`, para que a
geometria afirmada esteja visivel. Tiles de 8 px: a celula (c, l) ocupa
os pixels [8c, 8c + 8) x [8l, 8l + 8). Um corpo de 8x8 com anchor
CENTER em (12, 20) ocupa [8, 16) x [16, 24) -- encostado na coluna 2
pela esquerda, sem sobrepor.
"""

import pytest

from engine.math.anchor import Anchor
from engine.math.rect import Rect
from engine.math.vector2d import Vector2D
from engine.physics.collision import Collision
from engine.scene.body import Body
from engine.scene.node import Node
from tests.conftest import SpyTileSource

WALL = (1, 0)
FLOOR = (1, 1)
LEGEND = {"#": WALL, ".": FLOOR}
SOLID = {WALL}


def world(*rows):
    return Collision(SpyTileSource.from_rows(list(rows), LEGEND), SOLID)


def body_at(x, y, size=8.0, anchor=Anchor.CENTER):
    body = Body("B", size=Vector2D(size, size), anchor=anchor)
    body.transform.position = Vector2D(x, y)

    return body


def position(body):
    return body.transform.position


# Uma parede vertical na coluna 2, linhas 1 a 3: pixels [16, 24) em x.
VERTICAL_WALL = (
    ".....",
    "..#..",
    "..#..",
    "..#..",
    ".....",
)

# Uma parede horizontal na linha 2, colunas 1 a 3: pixels [16, 24) em y.
HORIZONTAL_WALL = (
    ".....",
    ".....",
    ".###.",
    ".....",
    ".....",
)


class TestFreeMovement:
    def test_a_body_moves_by_the_whole_delta_on_open_floor(self):
        collision = world(*VERTICAL_WALL)
        body = body_at(4.0, 4.0)

        collision.move_and_slide(body, Vector2D(1.0, 2.0))

        assert position(body) == Vector2D(5.0, 6.0)

    def test_a_zero_delta_changes_nothing(self):
        collision = world(*VERTICAL_WALL)
        body = body_at(12.0, 20.0)

        collision.move_and_slide(body, Vector2D())

        assert position(body) == Vector2D(12.0, 20.0)


class TestEachAxisAlone:
    """Resolucao em cada eixo isolado, nos dois sentidos."""

    def test_moving_right_stops_at_the_wall_face(self):
        collision = world(*VERTICAL_WALL)
        body = body_at(10.0, 20.0)  # [6, 14): 2 px antes da parede

        collision.move_and_slide(body, Vector2D(5.0, 0.0))

        # Andou 2 dos 5, e a borda direita parou EXATAMENTE em 16.
        assert position(body) == Vector2D(12.0, 20.0)
        assert body.get_world_bounds().x + 8.0 == 16.0

    def test_moving_left_stops_at_the_wall_face(self):
        collision = world(*VERTICAL_WALL)
        body = body_at(30.0, 20.0)  # [26, 34): 2 px depois da parede

        collision.move_and_slide(body, Vector2D(-5.0, 0.0))

        assert position(body) == Vector2D(28.0, 20.0)
        assert body.get_world_bounds().x == 24.0

    def test_moving_down_stops_at_the_wall_face(self):
        collision = world(*HORIZONTAL_WALL)
        body = body_at(20.0, 10.0)  # y em [6, 14)

        collision.move_and_slide(body, Vector2D(0.0, 5.0))

        assert position(body) == Vector2D(20.0, 12.0)

    def test_moving_up_stops_at_the_wall_face(self):
        collision = world(*HORIZONTAL_WALL)
        body = body_at(20.0, 30.0)  # y em [26, 34)

        collision.move_and_slide(body, Vector2D(0.0, -5.0))

        assert position(body) == Vector2D(20.0, 28.0)

    def test_a_wall_on_one_axis_does_not_touch_the_other(self):
        collision = world(*VERTICAL_WALL)
        body = body_at(12.0, 20.0)

        collision.move_and_slide(body, Vector2D(0.0, 3.0))

        assert position(body) == Vector2D(12.0, 23.0)


class TestSliding:
    """O ganho de resolver por eixo: a diagonal escorrega, nao gruda."""

    def test_diagonal_against_a_vertical_wall_slides_along_it(self):
        collision = world(*VERTICAL_WALL)
        body = body_at(12.0, 20.0)  # encostado na parede pela esquerda

        collision.move_and_slide(body, Vector2D(3.0, 2.0))

        # X barrado, Y inteiro.
        assert position(body) == Vector2D(12.0, 22.0)

    def test_diagonal_against_a_horizontal_wall_slides_along_it(self):
        collision = world(*HORIZONTAL_WALL)
        body = body_at(20.0, 12.0)  # encostado na parede por cima

        collision.move_and_slide(body, Vector2D(2.0, 3.0))

        assert position(body) == Vector2D(22.0, 12.0)

    def test_sliding_along_a_wall_for_many_frames_never_jitters(self):
        # O caso do HM: andar colado na parede com a diagonal segurada.
        # Se a parede empurrasse todo frame, o X oscilaria.
        collision = world(*VERTICAL_WALL)
        body = body_at(12.0, 12.0)

        for _ in range(10):
            collision.move_and_slide(body, Vector2D(1.2, 1.0))

        assert position(body) == Vector2D(12.0, 22.0)

    def test_inside_a_concave_corner_both_axes_stop(self):
        # Um canto: parede em cima e a esquerda. O corpo esta na quina,
        # e empurrar para a diagonal de dentro nao move nada -- e nao
        # vibra.
        collision = world(
            ".....",
            ".###.",
            ".#...",
            ".#...",
            ".....",
        )
        body = body_at(20.0, 20.0)  # [16, 24)^2, encostado nos dois

        for _ in range(5):
            collision.move_and_slide(body, Vector2D(-2.0, -2.0))

        assert position(body) == Vector2D(20.0, 20.0)

    def test_a_lone_diagonal_cell_is_not_entered_and_the_body_slides(self):
        # Celula solida so na diagonal, sem as duas ortogonais. O caso
        # em que resolver o vetor inteiro daria uma normal ambigua; por
        # eixo, X passa (a coluna nova esta livre na linha atual) e Y
        # e barrado (a linha nova tem a celula, nas colunas cobertas).
        collision = world(
            "....",
            "....",
            "..#.",
            "....",
        )
        body = body_at(12.0, 12.0)  # [8, 16)^2, diagonal a (2, 2)

        collision.move_and_slide(body, Vector2D(2.0, 2.0))

        assert position(body) == Vector2D(14.0, 12.0)
        assert not body.get_world_bounds().intersects(
            Rect(16.0, 16.0, 8.0, 8.0)
        )


class TestTouchingIsNotColliding:
    """O intervalo semiaberto do Rect, visto pela grade."""

    def test_a_body_flush_against_the_wall_is_not_pushed(self):
        collision = world(*VERTICAL_WALL)
        body = body_at(12.0, 20.0)  # borda direita em 16.0, a face

        collision.move_and_slide(body, Vector2D(0.0, 1.0))

        assert position(body).x == 12.0

    def test_pushing_into_the_wall_while_flush_is_idempotent(self):
        collision = world(*VERTICAL_WALL)
        body = body_at(12.0, 20.0)

        for _ in range(50):
            collision.move_and_slide(body, Vector2D(1.0, 0.0))

        assert position(body) == Vector2D(12.0, 20.0)

    def test_the_edge_survives_float_drift(self):
        # Tamanho impar e delta fracionario: o pior caso para a borda
        # cair em 16.0000001 e a coluna 2 passar a contar como "ja
        # coberta" -- momento em que o corpo atravessaria em silencio.
        collision = world(*VERTICAL_WALL)
        body = body_at(10.0, 20.0, size=7.3)

        for _ in range(500):
            collision.move_and_slide(body, Vector2D(0.7, 0.0))

        right = body.get_world_bounds().x + 7.3

        assert right == pytest.approx(16.0, abs=1e-6)
        assert right <= 16.0 + 1e-6


class TestShapesAndAnchors:
    def test_a_box_wider_than_a_tile_is_stopped_by_a_single_cell(self):
        # Corpo de 16x16 contra uma parede de UMA celula no meio da
        # borda dele: a linha inteira coberta e consultada, nao so a
        # do centro.
        collision = world(
            "......",
            "......",
            "...#..",
            "......",
            "......",
            "......",
        )
        body = body_at(12.0, 20.0, size=16.0)  # [4, 20) x [12, 28)

        collision.move_and_slide(body, Vector2D(6.0, 0.0))

        assert position(body) == Vector2D(16.0, 20.0)

    def test_a_top_left_anchor_collides_by_its_box_not_its_origin(self):
        collision = world(*VERTICAL_WALL)
        body = body_at(6.0, 16.0, anchor=Anchor.TOP_LEFT)  # [6, 14)

        collision.move_and_slide(body, Vector2D(5.0, 0.0))

        assert position(body) == Vector2D(8.0, 16.0)

    def test_a_bottom_center_anchor_collides_by_its_box(self):
        collision = world(*HORIZONTAL_WALL)
        body = body_at(20.0, 14.0, anchor=Anchor.BOTTOM_CENTER)  # y [6, 14)

        collision.move_and_slide(body, Vector2D(0.0, 5.0))

        assert position(body) == Vector2D(20.0, 16.0)

    def test_a_fractional_position_is_resolved_exactly_to_the_face(self):
        collision = world(*VERTICAL_WALL)
        body = body_at(11.5, 20.0)

        collision.move_and_slide(body, Vector2D(1.0, 0.0))

        assert position(body) == Vector2D(12.0, 20.0)

    def test_a_body_without_size_is_a_marker_and_passes_through(self):
        # Area zero nao colide com nada -- a mesma regra do
        # Rect.intersects. Um no sem tamanho e um marco de spawn.
        collision = world(*VERTICAL_WALL)
        body = body_at(12.0, 20.0, size=0.0)

        collision.move_and_slide(body, Vector2D(8.0, 0.0))

        assert position(body) == Vector2D(20.0, 20.0)


class TestFastBodies:
    def test_a_delta_larger_than_a_tile_does_not_tunnel(self):
        # Todas as colunas cruzadas sao vistas, nao so a de chegada.
        collision = world(*VERTICAL_WALL)
        body = body_at(4.0, 20.0)  # [0, 8)

        collision.move_and_slide(body, Vector2D(30.0, 0.0))

        assert position(body) == Vector2D(12.0, 20.0)

    def test_a_fast_diagonal_still_slides(self):
        collision = world(*VERTICAL_WALL)
        body = body_at(4.0, 12.0)

        collision.move_and_slide(body, Vector2D(30.0, 10.0))

        assert position(body) == Vector2D(12.0, 22.0)


class TestTheEdgeOfTheMap:
    def test_outside_the_map_is_solid(self):
        # Mapa 2x2 de chao, 16x16 px, sem parede pintada: a borda do
        # mapa e o que segura o corpo.
        collision = world("..", "..")
        body = body_at(4.0, 4.0)

        collision.move_and_slide(body, Vector2D(-3.0, -3.0))
        assert position(body) == Vector2D(4.0, 4.0)

        collision.move_and_slide(body, Vector2D(30.0, 30.0))
        assert position(body) == Vector2D(12.0, 12.0)


class TestWhatIsNotPrevented:
    def test_a_body_that_starts_inside_a_wall_is_not_ejected(self):
        # Documentado, e nao acidental: as celulas dele nao sao novas, e
        # nao ha direcao certa para empurrar quem ja esta do outro
        # lado. move_and_slide impede ENTRAR.
        collision = world(*VERTICAL_WALL)
        body = body_at(20.0, 20.0)  # [16, 24): dentro da coluna 2

        collision.move_and_slide(body, Vector2D(1.0, 0.0))

        assert position(body) == Vector2D(21.0, 20.0)


class TestTheBodyLivesInATree:
    def test_a_translated_parent_is_accounted_for(self):
        # O corpo esta pendurado numa camada deslocada. A parede e em
        # coordenadas de MUNDO; a escrita e na posicao LOCAL.
        collision = world(*VERTICAL_WALL)
        layer = Node("Layer")
        layer.transform.position = Vector2D(100.0, 100.0)

        body = body_at(-90.0, -80.0)  # mundo (10, 20): [6, 14)
        layer.add_child(body)

        collision.move_and_slide(body, Vector2D(5.0, 0.0))

        assert position(body) == Vector2D(-88.0, -80.0)
        assert body.get_world_position() == Vector2D(12.0, 20.0)


class TestTheGrid:
    def test_cell_at_divides_by_the_tile_size(self):
        collision = world("....", "....")

        assert collision.cell_at(Vector2D(0.0, 0.0)) == (0, 0)
        assert collision.cell_at(Vector2D(7.9, 15.9)) == (0, 1)
        assert collision.cell_at(Vector2D(8.0, 16.0)) == (1, 2)

    def test_cell_at_rounds_down_in_negative_coordinates(self):
        # int() truncaria (-0.5) para 0, e a coluna -1 nao existiria.
        collision = world("....", "....")

        assert collision.cell_at(Vector2D(-0.5, -0.5)) == (-1, -1)

    def test_is_solid_reads_the_game_set(self):
        collision = world("#.", "..")

        assert collision.is_solid(0, 0)
        assert not collision.is_solid(1, 0)

    def test_is_solid_outside_the_map_is_true(self):
        collision = world("..", "..")

        assert collision.is_solid(-1, 0)
        assert collision.is_solid(0, 2)

    def test_the_tile_size_comes_from_the_source(self):
        collision = Collision(
            SpyTileSource.from_rows(["."], LEGEND, tile_size=16), SOLID
        )

        assert collision.tile_size == 16
        assert collision.cell_at(Vector2D(15.0, 0.0)) == (0, 0)
        assert collision.cell_at(Vector2D(16.0, 0.0)) == (1, 0)

    def test_the_solid_set_is_copied(self):
        # O jogo pode passar uma lista e muda-la depois sem afetar a
        # colisao -- a pergunta "e solido?" nao muda no meio do frame.
        solid = [WALL]
        collision = Collision(SpyTileSource.from_rows(["#"], LEGEND), solid)

        solid.clear()

        assert collision.is_solid(0, 0)
