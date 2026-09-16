"""Collision.raycast: DDA pela grade, slab contra os corpos.

Mesma convencao do test_move_and_slide: tiles de 8 px, cenario
desenhado em texto. A celula (c, l) ocupa [8c, 8c + 8) x [8l, 8l + 8).
"""

import math

import pytest

from engine.math.vector2d import Vector2D
from engine.physics.collision import Collision
from engine.physics.raycast_hit import RaycastHit
from engine.scene.body import Body
from tests.conftest import SpyTileSource

WALL = (1, 0)
FLOOR = (1, 1)
LEGEND = {"#": WALL, ".": FLOOR}
SOLID = {WALL}

RIGHT = Vector2D(1.0, 0.0)
LEFT = Vector2D(-1.0, 0.0)
DOWN = Vector2D(0.0, 1.0)
UP = Vector2D(0.0, -1.0)


def world(*rows):
    return Collision(SpyTileSource.from_rows(list(rows), LEGEND), SOLID)


def body_at(x, y, size=8.0):
    body = Body("B", size=Vector2D(size, size))
    body.transform.position = Vector2D(x, y)

    return body


# Uma parede vertical na coluna 4: pixels [32, 40) em x.
VERTICAL_WALL = (
    "......",
    "....#.",
    "....#.",
    "....#.",
    "....#.",
    "......",
)

# Um corredor aberto 8x8, sem parede pintada: so a borda do mapa.
OPEN = tuple(["........"] * 8)


class TestTheGrid:
    """DDA contra as paredes, sem corpo nenhum registrado."""

    def test_a_ray_stops_at_the_first_wall(self):
        collision = world(*VERTICAL_WALL)

        hit = collision.raycast(Vector2D(4.0, 20.0), RIGHT, 100.0)

        assert hit == RaycastHit(Vector2D(32.0, 20.0), LEFT, 28.0, None)

    def test_no_wall_within_range_is_none(self):
        collision = world(*VERTICAL_WALL)

        assert collision.raycast(Vector2D(4.0, 20.0), RIGHT, 20.0) is None

    def test_a_wall_exactly_at_max_distance_is_hit(self):
        collision = world(*VERTICAL_WALL)

        hit = collision.raycast(Vector2D(4.0, 20.0), RIGHT, 28.0)

        assert hit is not None and hit.distance == 28.0

    def test_the_normal_faces_the_ray_on_each_side(self):
        # Uma celula solida no meio; quatro raios, um de cada lado.
        collision = world(
            ".....",
            ".....",
            "..#..",
            ".....",
            ".....",
        )
        center = Vector2D(20.0, 20.0)

        cases = [
            (Vector2D(4.0, 20.0), RIGHT, LEFT),
            (Vector2D(36.0, 20.0), LEFT, RIGHT),
            (Vector2D(20.0, 4.0), DOWN, UP),
            (Vector2D(20.0, 36.0), UP, DOWN),
        ]

        for origin, direction, expected_normal in cases:
            hit = collision.raycast(origin, direction, 100.0)

            assert hit is not None
            assert hit.normal == expected_normal
            assert hit.distance == 12.0
            assert hit.point.distance_to(center) == pytest.approx(4.0)

    def test_parallel_to_an_axis_walks_a_single_row(self):
        # Direcao sem componente Y: o eixo Y nunca avanca, e o raio
        # atravessa a linha inteira ate a coluna solida, sem visitar
        # linha vizinha nenhuma.
        collision = world(
            "#######",
            "#.....#",
            "#######",
        )

        hit = collision.raycast(Vector2D(9.0, 12.0), RIGHT, 100.0)

        assert hit == RaycastHit(Vector2D(48.0, 12.0), LEFT, 39.0, None)

    def test_a_diagonal_ray_lands_on_the_face_it_crossed(self):
        collision = world(*VERTICAL_WALL)
        direction = Vector2D(1.0, 1.0)

        hit = collision.raycast(Vector2D(20.0, 8.0), direction, 100.0)

        # Entra na coluna 4 em x = 32, que esta a 12 em X e portanto
        # 12 em Y: (32, 20), a 12 * sqrt(2) de distancia.
        assert hit is not None
        assert hit.point.x == pytest.approx(32.0)
        assert hit.point.y == pytest.approx(20.0)
        assert hit.normal == LEFT
        assert hit.distance == pytest.approx(12.0 * math.sqrt(2.0))

    def test_starting_exactly_on_a_boundary_going_forward(self):
        # x = 16.0 pertence a coluna 2 (semiaberto); a proxima divisa
        # esta a 8, e a parede em 32 a 16.
        collision = world(*VERTICAL_WALL)

        hit = collision.raycast(Vector2D(16.0, 20.0), RIGHT, 100.0)

        assert hit is not None and hit.distance == 16.0

    def test_starting_exactly_on_a_wall_face_looking_at_it(self):
        # x = 40.0 e a face DIREITA da parede: fora dela, encostado.
        # Olhando para a esquerda, o raio entra na parede a distancia
        # zero -- e a normal e a da face, nao zero, porque o raio nao
        # nasceu dentro.
        collision = world(*VERTICAL_WALL)

        hit = collision.raycast(Vector2D(40.0, 20.0), LEFT, 100.0)

        assert hit == RaycastHit(Vector2D(40.0, 20.0), RIGHT, 0.0, None)

    def test_starting_inside_a_solid_cell_hits_at_the_origin(self):
        # Sem face para nomear: normal zero. E o caso da bala cuja
        # posicao anterior ja estava na parede -- o tiro acabou.
        collision = world(*VERTICAL_WALL)
        origin = Vector2D(36.0, 20.0)

        hit = collision.raycast(origin, RIGHT, 100.0)

        assert hit == RaycastHit(origin, Vector2D(), 0.0, None)

    def test_outside_the_map_is_a_wall(self):
        collision = world(*OPEN)

        hit = collision.raycast(Vector2D(60.0, 30.0), RIGHT, 100.0)

        assert hit == RaycastHit(Vector2D(64.0, 30.0), LEFT, 4.0, None)

    def test_starting_outside_the_map_hits_at_the_origin(self):
        collision = world(*OPEN)
        origin = Vector2D(-10.0, 30.0)

        assert collision.raycast(origin, RIGHT, 100.0) == RaycastHit(
            origin, Vector2D(), 0.0, None
        )

    def test_through_an_exact_corner_the_diagonal_cell_is_hit(self):
        # O raio passa pelo canto (16, 16) e a unica celula solida e a
        # diagonal (2, 2). No empate Y avanca e X vem logo atras, a
        # mesma distancia: a celula diagonal e visitada, e acertada.
        collision = world(
            "....",
            "....",
            "..#.",
            "....",
        )

        hit = collision.raycast(Vector2D(8.0, 8.0), Vector2D(1.0, 1.0), 100.0)

        assert hit is not None
        assert hit.distance == pytest.approx(8.0 * math.sqrt(2.0))
        assert hit.point.x == pytest.approx(16.0)
        assert hit.point.y == pytest.approx(16.0)

    def test_cost_is_proportional_to_distance_not_map_size(self):
        # O que faz o DDA ser DDA: um raio curto num mapa grande toca
        # poucas celulas. Conta as leituras da porta.
        reads = []

        class CountingSource(SpyTileSource):
            def get_tile(self, column, row):
                reads.append((column, row))
                return super().get_tile(column, row)

        source = CountingSource.from_rows(["." * 200] * 200, LEGEND)
        collision = Collision(source, SOLID)

        collision.raycast(Vector2D(804.0, 804.0), RIGHT, 40.0)

        # 5 tiles de 8 px em 40 px, mais a celula de origem.
        assert len(reads) <= 6


class TestTheDirection:
    def test_the_direction_is_normalized_so_distance_is_in_world_units(
        self,
    ):
        collision = world(*VERTICAL_WALL)

        short = collision.raycast(
            Vector2D(4.0, 20.0), Vector2D(1.0, 0.0), 100.0
        )
        long = collision.raycast(
            Vector2D(4.0, 20.0), Vector2D(7.0, 0.0), 100.0
        )

        assert short == long

    def test_a_zero_direction_raises(self):
        collision = world(*VERTICAL_WALL)

        with pytest.raises(ValueError):
            collision.raycast(Vector2D(4.0, 20.0), Vector2D(), 100.0)


class TestBodies:
    """Slab contra a caixa de cada corpo registrado."""

    def test_a_body_in_the_path_is_hit_on_its_near_face(self):
        collision = world(*OPEN)
        body = body_at(30.0, 20.0)  # [26, 34) x [16, 24)
        collision.add_body(body)

        hit = collision.raycast(Vector2D(4.0, 20.0), RIGHT, 100.0)

        assert hit == RaycastHit(Vector2D(26.0, 20.0), LEFT, 22.0, body)

    def test_the_normal_is_the_face_the_ray_entered(self):
        collision = world(*OPEN)
        body = body_at(30.0, 30.0)
        collision.add_body(body)

        from_above = collision.raycast(Vector2D(30.0, 4.0), DOWN, 100.0)
        from_left = collision.raycast(Vector2D(4.0, 30.0), RIGHT, 100.0)

        assert from_above is not None and from_above.normal == UP
        assert from_left is not None and from_left.normal == LEFT

    def test_a_body_behind_the_origin_is_not_hit(self):
        collision = world(*OPEN)
        collision.add_body(body_at(10.0, 20.0))

        assert collision.raycast(Vector2D(30.0, 20.0), RIGHT, 100.0) == (
            RaycastHit(Vector2D(64.0, 20.0), LEFT, 34.0, None)
        )

    def test_a_body_beyond_max_distance_is_not_hit(self):
        collision = world(*OPEN)
        collision.add_body(body_at(30.0, 20.0))

        assert collision.raycast(Vector2D(4.0, 20.0), RIGHT, 20.0) is None

    def test_a_body_exactly_at_max_distance_is_hit(self):
        # Mesma regra da parede: o alcance e inclusivo.
        collision = world(*OPEN)
        body = body_at(30.0, 20.0)
        collision.add_body(body)

        hit = collision.raycast(Vector2D(4.0, 20.0), RIGHT, 22.0)

        assert hit is not None and hit.body is body

    def test_a_ray_that_misses_the_box_to_the_side_is_not_a_hit(self):
        collision = world(*OPEN)
        collision.add_body(body_at(30.0, 20.0))  # y em [16, 24)

        hit = collision.raycast(Vector2D(4.0, 30.0), RIGHT, 100.0)

        assert hit is not None and hit.body is None

    def test_the_top_edge_is_inside_and_the_bottom_edge_is_not(self):
        # Semiaberto, como o Rect: um raio horizontal exatamente sobre
        # y = 16 toca o corpo; sobre y = 24, nao.
        collision = world(*OPEN)
        body = body_at(30.0, 20.0)  # y em [16, 24)
        collision.add_body(body)

        on_top = collision.raycast(Vector2D(4.0, 16.0), RIGHT, 100.0)
        on_bottom = collision.raycast(Vector2D(4.0, 24.0), RIGHT, 100.0)

        assert on_top is not None and on_top.body is body
        assert on_bottom is not None and on_bottom.body is None

    def test_a_diagonal_ray_enters_by_the_nearer_face(self):
        collision = world(*OPEN)
        body = body_at(30.0, 30.0)  # [26, 34)^2
        collision.add_body(body)

        # De (10, 20) na diagonal o raio chega em x = 26 com y = 36, ja
        # abaixo da caixa: passa ao lado, e o que ele acha e a borda do
        # mapa.
        miss = collision.raycast(
            Vector2D(10.0, 20.0), Vector2D(1.0, 1.0), 100.0
        )

        assert miss is not None and miss.body is None

        # De (18, 20) chega em x = 26 com y = 28, dentro da faixa
        # [26, 34): entra pela face esquerda.
        hit = collision.raycast(
            Vector2D(18.0, 20.0), Vector2D(1.0, 1.0), 100.0
        )

        assert hit is not None
        assert hit.body is body
        assert hit.normal == LEFT
        assert hit.point.x == pytest.approx(26.0)
        assert hit.point.y == pytest.approx(28.0)

    def test_starting_inside_a_body_hits_it_at_the_origin(self):
        collision = world(*OPEN)
        body = body_at(30.0, 20.0)
        collision.add_body(body)
        origin = Vector2D(30.0, 20.0)

        assert collision.raycast(origin, RIGHT, 100.0) == RaycastHit(
            origin, Vector2D(), 0.0, body
        )

    def test_a_body_without_size_is_never_hit(self):
        collision = world(*OPEN)
        collision.add_body(body_at(30.0, 20.0, size=0.0))

        hit = collision.raycast(Vector2D(4.0, 20.0), RIGHT, 100.0)

        assert hit is not None and hit.body is None

    def test_a_body_that_is_not_registered_is_invisible(self):
        collision = world(*OPEN)
        body_at(30.0, 20.0)  # nunca registrado

        hit = collision.raycast(Vector2D(4.0, 20.0), RIGHT, 100.0)

        assert hit is not None and hit.body is None


class TestWhoWins:
    def test_the_nearest_wins_body_before_wall(self):
        collision = world(*VERTICAL_WALL)
        body = body_at(20.0, 20.0)  # [16, 24): antes da parede em 32
        collision.add_body(body)

        hit = collision.raycast(Vector2D(4.0, 20.0), RIGHT, 100.0)

        assert hit is not None and hit.body is body and hit.distance == 12.0

    def test_the_nearest_wins_wall_before_body(self):
        collision = world(*VERTICAL_WALL)
        collision.add_body(body_at(44.0, 20.0))  # do outro lado da parede

        hit = collision.raycast(Vector2D(4.0, 20.0), RIGHT, 100.0)

        assert hit is not None and hit.body is None and hit.distance == 28.0

    def test_on_a_tie_the_wall_wins(self):
        # Corpo encostado na parede pelo lado de la: a bala parou na
        # parede antes.
        collision = world(*VERTICAL_WALL)
        collision.add_body(body_at(36.0, 20.0))  # [32, 40): sobre a parede

        hit = collision.raycast(Vector2D(4.0, 20.0), RIGHT, 100.0)

        assert hit is not None and hit.body is None

    def test_between_two_bodies_the_nearest_wins(self):
        collision = world(*OPEN)
        far = body_at(50.0, 20.0)
        near = body_at(30.0, 20.0)
        collision.add_body(far)
        collision.add_body(near)

        hit = collision.raycast(Vector2D(4.0, 20.0), RIGHT, 100.0)

        assert hit is not None and hit.body is near

    def test_ignored_bodies_are_skipped(self):
        # O inimigo lanca o raio de dentro da propria caixa: sem
        # `ignore` acertaria a si mesmo a distancia zero.
        collision = world(*OPEN)
        shooter = body_at(10.0, 20.0)
        target = body_at(30.0, 20.0)
        collision.add_body(shooter)
        collision.add_body(target)

        hit = collision.raycast(
            Vector2D(10.0, 20.0), RIGHT, 100.0, ignore=(shooter,)
        )

        assert hit is not None and hit.body is target
