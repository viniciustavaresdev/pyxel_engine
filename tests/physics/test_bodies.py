"""A lista de corpos da Collision, e a consulta por area."""

from engine.math.rect import Rect
from engine.math.vector2d import Vector2D
from engine.physics.collision import Collision
from engine.scene.body import Body
from tests.conftest import SpyTileSource

LEGEND = {".": (1, 1)}


def collision():
    return Collision(SpyTileSource.from_rows(["...."] * 4, LEGEND), set())


def body_at(x, y, size=8.0):
    body = Body("B", size=Vector2D(size, size))
    body.transform.position = Vector2D(x, y)

    return body


class TestTheList:
    def test_it_starts_empty(self):
        assert collision().bodies == ()

    def test_add_and_remove(self):
        c = collision()
        body = body_at(0.0, 0.0)

        c.add_body(body)
        assert c.bodies == (body,)

        c.remove_body(body)
        assert c.bodies == ()

    def test_adding_twice_keeps_one(self):
        # Um corpo em dobro seria acertado duas vezes.
        c = collision()
        body = body_at(0.0, 0.0)

        c.add_body(body)
        c.add_body(body)

        assert c.bodies == (body,)

    def test_removing_an_unregistered_body_is_a_no_op(self):
        c = collision()

        c.remove_body(body_at(0.0, 0.0))

        assert c.bodies == ()

    def test_the_order_is_the_order_of_registration(self):
        c = collision()
        first, second = body_at(0.0, 0.0), body_at(10.0, 0.0)

        c.add_body(first)
        c.add_body(second)

        assert c.bodies == (first, second)

    def test_bodies_is_a_snapshot(self):
        c = collision()
        body = body_at(0.0, 0.0)
        c.add_body(body)

        snapshot = c.bodies
        c.remove_body(body)

        assert snapshot == (body,)


class TestBodiesIn:
    def test_overlapping_bodies_are_returned(self):
        c = collision()
        inside = body_at(10.0, 10.0)  # [6, 14)^2
        outside = body_at(30.0, 30.0)
        c.add_body(inside)
        c.add_body(outside)

        assert c.bodies_in(Rect(0.0, 0.0, 16.0, 16.0)) == [inside]

    def test_touching_is_not_inside(self):
        # A regra semiaberta do Rect: a caixa [16, 24) encosta na area
        # [0, 16) e nao a sobrepoe.
        c = collision()
        c.add_body(body_at(20.0, 8.0))

        assert c.bodies_in(Rect(0.0, 0.0, 16.0, 16.0)) == []

    def test_a_body_without_size_is_never_inside(self):
        c = collision()
        c.add_body(body_at(8.0, 8.0, size=0.0))

        assert c.bodies_in(Rect(0.0, 0.0, 16.0, 16.0)) == []

    def test_an_empty_area_contains_nothing(self):
        c = collision()
        c.add_body(body_at(8.0, 8.0))

        assert c.bodies_in(Rect(8.0, 8.0, 0.0, 0.0)) == []

    def test_the_result_is_a_fresh_list_in_registration_order(self):
        c = collision()
        a, b = body_at(4.0, 4.0), body_at(12.0, 4.0)
        c.add_body(a)
        c.add_body(b)
        area = Rect(0.0, 0.0, 32.0, 32.0)

        first = c.bodies_in(area)
        first.clear()

        assert c.bodies_in(area) == [a, b]

    def test_a_removed_body_is_no_longer_found(self):
        c = collision()
        body = body_at(8.0, 8.0)
        c.add_body(body)
        c.remove_body(body)

        assert c.bodies_in(Rect(0.0, 0.0, 32.0, 32.0)) == []

    def test_the_box_is_the_world_bounds(self):
        # Um corpo pendurado numa camada deslocada e achado onde ele
        # esta no MUNDO.
        from engine.scene.node import Node

        c = collision()
        layer = Node("Layer")
        layer.transform.position = Vector2D(100.0, 100.0)
        body = body_at(-92.0, -92.0)  # mundo (8, 8)
        layer.add_child(body)
        c.add_body(body)

        assert c.bodies_in(Rect(0.0, 0.0, 16.0, 16.0)) == [body]
        assert c.bodies_in(Rect(-100.0, -100.0, 16.0, 16.0)) == []
