import dataclasses

import pytest

from engine.math.anchor import Anchor
from engine.math.vector2d import Vector2D


class TestConstants:

    def test_center_is_the_middle_of_the_box(self):
        assert (Anchor.CENTER.x, Anchor.CENTER.y) == (0.5, 0.5)

    def test_top_left_is_the_origin_of_the_box(self):
        assert (Anchor.TOP_LEFT.x, Anchor.TOP_LEFT.y) == (0.0, 0.0)

    def test_bottom_center_puts_the_origin_at_the_feet(self):
        assert (Anchor.BOTTOM_CENTER.x, Anchor.BOTTOM_CENTER.y) == (0.5, 1.0)


class TestImmutability:

    def test_an_anchor_cannot_be_written_to(self):
        # frozen porque as constantes sao compartilhadas: sem isso, um
        # no que escrevesse em Anchor.CENTER moveria todos os outros.
        with pytest.raises(dataclasses.FrozenInstanceError):
            Anchor.CENTER.x = 0.0  # type: ignore[misc]


class TestPointIn:
    """Onde o anchor cai dentro da caixa, a partir do canto."""

    def test_top_left_lands_on_the_corner(self):
        size = Vector2D(8.0, 4.0)

        assert Anchor.TOP_LEFT.point_in(size) == Vector2D(0.0, 0.0)

    def test_center_lands_on_half_the_size(self):
        size = Vector2D(8.0, 4.0)

        assert Anchor.CENTER.point_in(size) == Vector2D(4.0, 2.0)

    def test_bottom_right_lands_on_the_far_corner(self):
        size = Vector2D(8.0, 4.0)

        assert Anchor.BOTTOM_RIGHT.point_in(size) == Vector2D(8.0, 4.0)

    def test_scales_with_the_box_instead_of_being_fixed_in_pixels(self):
        # O motivo de o anchor ser normalizado: o mesmo valor serve para
        # qualquer tamanho, e continua valendo quando a escala muda.
        assert Anchor.CENTER.point_in(Vector2D(32.0, 48.0)) == Vector2D(
            16.0, 24.0
        )


class TestToCenter:
    """Deslocamento da origem ate o centro da caixa."""

    def test_center_needs_no_correction(self):
        # O caso comum, e o que faz a conversao sumir quando o anchor
        # ja e o centro.
        assert Anchor.CENTER.to_center(Vector2D(8.0, 4.0)) == Vector2D(
            0.0, 0.0
        )

    def test_top_left_moves_half_a_box_forward(self):
        assert Anchor.TOP_LEFT.to_center(Vector2D(8.0, 4.0)) == Vector2D(
            4.0, 2.0
        )

    def test_bottom_center_moves_half_a_box_up(self):
        assert Anchor.BOTTOM_CENTER.to_center(Vector2D(8.0, 4.0)) == Vector2D(
            0.0, -2.0
        )

    def test_is_the_opposite_of_point_in_measured_from_the_center(self):
        # Relacao entre os dois metodos: point_in mede a partir do
        # canto, to_center a partir do centro.
        size = Vector2D(10.0, 6.0)
        anchor = Anchor(0.25, 0.75)

        half = size / 2.0
        expected = half - anchor.point_in(size)

        assert anchor.to_center(size).x == pytest.approx(expected.x)
        assert anchor.to_center(size).y == pytest.approx(expected.y)
