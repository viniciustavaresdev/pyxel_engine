import dataclasses

import pytest

from engine.math.rect import Rect
from engine.math.vector2d import Vector2D


class TestConstruction:

    def test_holds_the_four_components(self):
        rect = Rect(1.0, 2.0, 3.0, 4.0)

        assert (rect.x, rect.y, rect.width, rect.height) == (
            1.0,
            2.0,
            3.0,
            4.0,
        )

    def test_equality_is_by_value(self):
        assert Rect(1.0, 2.0, 3.0, 4.0) == Rect(1.0, 2.0, 3.0, 4.0)

    def test_differs_when_any_component_differs(self):
        base = Rect(1.0, 2.0, 3.0, 4.0)

        assert base != Rect(9.0, 2.0, 3.0, 4.0)
        assert base != Rect(1.0, 9.0, 3.0, 4.0)
        assert base != Rect(1.0, 2.0, 9.0, 4.0)
        assert base != Rect(1.0, 2.0, 3.0, 9.0)


class TestImmutability:

    def test_cannot_be_written_to(self):
        # frozen porque a regiao de um sprite e definida uma vez e
        # compartilhada por todo frame que a desenha. Sem isto, uma
        # constante de classe poderia ser corrompida por um no.
        rect = Rect(1.0, 2.0, 3.0, 4.0)

        with pytest.raises(dataclasses.FrozenInstanceError):
            rect.x = 99.0  # type: ignore[misc]

    def test_is_hashable(self):
        # Consequencia util do frozen: serve de chave, o que permite
        # cachear por regiao mais tarde.
        assert len({Rect(0.0, 0.0, 8.0, 8.0), Rect(0.0, 0.0, 8.0, 8.0)}) == 1


class TestDerivedVectors:

    def test_position_is_the_top_left(self):
        assert Rect(1.0, 2.0, 3.0, 4.0).position == Vector2D(1.0, 2.0)

    def test_size_is_width_and_height(self):
        assert Rect(1.0, 2.0, 3.0, 4.0).size == Vector2D(3.0, 4.0)

    def test_the_derived_vector_cannot_be_used_to_reach_the_rect(self):
        # Antes isto verificava que a property devolvia um objeto
        # fresco, porque escrever num Vector2D guardado furaria o
        # frozen do Rect. Com o vetor imutavel a rota simplesmente nao
        # existe mais -- e e isso que se afirma agora.
        rect = Rect(1.0, 2.0, 3.0, 4.0)

        with pytest.raises(dataclasses.FrozenInstanceError):
            rect.position.x = 99.0  # type: ignore[misc]

        assert rect.x == 1.0

    def test_each_access_returns_a_distinct_object(self):
        rect = Rect(1.0, 2.0, 3.0, 4.0)

        assert rect.position is not rect.position


class TestCenter:

    def test_center_is_half_a_size_past_the_corner(self):
        assert Rect(10.0, 20.0, 8.0, 4.0).center == Vector2D(14.0, 22.0)

    def test_center_of_an_empty_rect_is_its_corner(self):
        assert Rect(10.0, 20.0, 0.0, 0.0).center == Vector2D(10.0, 20.0)


class TestFromCenterSize:

    def test_builds_the_corner_from_the_center(self):
        rect = Rect.from_center_size(Vector2D(14.0, 22.0), Vector2D(8.0, 4.0))

        assert rect == Rect(10.0, 20.0, 8.0, 4.0)

    def test_round_trips_through_the_center(self):
        # E a garantia que get_world_bounds depende: montar pelo centro
        # e ler o centro de volta nao pode deslocar nada.
        center = Vector2D(3.5, -7.25)
        size = Vector2D(9.0, 5.0)

        assert Rect.from_center_size(center, size).center == center

    def test_an_empty_box_sits_on_its_center(self):
        rect = Rect.from_center_size(Vector2D(5.0, 5.0), Vector2D(0.0, 0.0))

        assert rect == Rect(5.0, 5.0, 0.0, 0.0)


class TestContains:

    def test_a_point_inside_is_inside(self):
        assert Rect(0.0, 0.0, 10.0, 10.0).contains(Vector2D(5.0, 5.0))

    def test_a_point_outside_is_outside(self):
        rect = Rect(0.0, 0.0, 10.0, 10.0)

        assert not rect.contains(Vector2D(-1.0, 5.0))
        assert not rect.contains(Vector2D(5.0, -1.0))
        assert not rect.contains(Vector2D(11.0, 5.0))
        assert not rect.contains(Vector2D(5.0, 11.0))

    def test_the_top_left_corner_belongs_to_the_rect(self):
        # Intervalo semiaberto: a borda de cima e a da esquerda contam.
        assert Rect(0.0, 0.0, 10.0, 10.0).contains(Vector2D(0.0, 0.0))

    def test_the_bottom_right_corner_does_not(self):
        assert not Rect(0.0, 0.0, 10.0, 10.0).contains(Vector2D(10.0, 10.0))

    def test_neighbouring_boxes_do_not_share_a_point(self):
        # O que a regra semiaberta compra: num grid de tiles, um ponto
        # sobre a divisa cai em exatamente um tile.
        left = Rect(0.0, 0.0, 10.0, 10.0)
        right = Rect(10.0, 0.0, 10.0, 10.0)
        on_the_seam = Vector2D(10.0, 5.0)

        assert not left.contains(on_the_seam)
        assert right.contains(on_the_seam)

    def test_an_empty_rect_contains_nothing(self):
        assert not Rect(5.0, 5.0, 0.0, 0.0).contains(Vector2D(5.0, 5.0))

    def test_a_mirrored_rect_is_read_normalized(self):
        # Sem o normalized() por dentro isto responderia "nunca", em
        # silencio: 0 <= x < -8 e falso para todo x.
        assert Rect(10.0, 0.0, -8.0, 8.0).contains(Vector2D(5.0, 4.0))


class TestIntersects:

    def test_overlapping_boxes_intersect(self):
        assert Rect(0.0, 0.0, 10.0, 10.0).intersects(
            Rect(5.0, 5.0, 10.0, 10.0)
        )

    def test_disjoint_boxes_do_not(self):
        assert not Rect(0.0, 0.0, 10.0, 10.0).intersects(
            Rect(20.0, 0.0, 10.0, 10.0)
        )

    def test_separated_on_a_single_axis_is_enough(self):
        # AABB: basta UM eixo em que uma termine antes de a outra
        # comecar. Sobrepostas em x, separadas em y.
        assert not Rect(0.0, 0.0, 10.0, 10.0).intersects(
            Rect(5.0, 50.0, 10.0, 10.0)
        )

    def test_touching_edges_do_not_intersect(self):
        # Mesma regra semiaberta: um jogador parado exatamente sobre o
        # chao nao esta afundado nele.
        assert not Rect(0.0, 0.0, 10.0, 10.0).intersects(
            Rect(10.0, 0.0, 10.0, 10.0)
        )

    def test_containment_counts_as_intersection(self):
        big = Rect(0.0, 0.0, 100.0, 100.0)
        small = Rect(40.0, 40.0, 5.0, 5.0)

        assert big.intersects(small)
        assert small.intersects(big)

    def test_is_symmetric(self):
        a = Rect(0.0, 0.0, 10.0, 10.0)
        b = Rect(5.0, 5.0, 10.0, 10.0)

        assert a.intersects(b) == b.intersects(a)

    def test_an_empty_rect_intersects_nothing(self):
        # Nem estando bem no meio da outra: a comparacao de bordas
        # sozinha diria que sim, e seria incoerente com o contains --
        # uma caixa que nao contem ponto nenhum nao pode dividir um
        # ponto com ninguem.
        empty = Rect(5.0, 5.0, 0.0, 0.0)
        big = Rect(0.0, 0.0, 10.0, 10.0)

        assert not empty.intersects(big)
        assert not big.intersects(empty)

    def test_a_zero_thickness_sliver_does_not_intersect_either(self):
        # Area zero por um eixo so. Uma linha nao tem corpo.
        sliver = Rect(5.0, 0.0, 0.0, 10.0)

        assert not sliver.intersects(Rect(0.0, 0.0, 10.0, 10.0))

    def test_a_mirrored_rect_is_read_normalized(self):
        mirrored = Rect(10.0, 0.0, -8.0, 8.0)

        assert mirrored.intersects(Rect(0.0, 0.0, 4.0, 4.0))


class TestNegativeSize:

    def test_accepts_a_negative_width(self):
        # Largura negativa e o idioma de espelhamento do backend --
        # virar um personagem sem uma segunda arte. Nao e erro.
        assert Rect(0.0, 0.0, -8.0, 8.0).width == -8.0

    def test_accepts_a_negative_height(self):
        assert Rect(0.0, 0.0, 8.0, -8.0).height == -8.0

    def test_normalizing_flips_the_width_onto_the_other_side(self):
        assert Rect(10.0, 0.0, -8.0, 8.0).normalized() == Rect(
            2.0, 0.0, 8.0, 8.0
        )

    def test_normalizing_flips_the_height_too(self):
        assert Rect(0.0, 10.0, 8.0, -8.0).normalized() == Rect(
            0.0, 2.0, 8.0, 8.0
        )

    def test_normalizing_preserves_the_area_covered(self):
        mirrored = Rect(10.0, 0.0, -8.0, 8.0)

        assert mirrored.normalized().center == mirrored.center

    def test_an_already_normal_rect_is_returned_untouched(self):
        # Devolve `self`, e nao uma copia: o caminho comum nao aloca.
        rect = Rect(0.0, 0.0, 8.0, 8.0)

        assert rect.normalized() is rect

    def test_the_mirrored_region_itself_is_left_alone(self):
        # normalized() devolve OUTRO rect. O original continua com o
        # sinal, porque e o sinal que o backend le para espelhar.
        mirrored = Rect(10.0, 0.0, -8.0, 8.0)

        mirrored.normalized()

        assert mirrored.width == -8.0
