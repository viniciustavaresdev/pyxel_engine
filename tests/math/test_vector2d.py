import dataclasses
import math

import pytest

from engine.math.transform import Transform
from engine.math.vector2d import Vector2D


class TestConstruction:
    def test_default_is_origin(self):
        assert Vector2D() == Vector2D(0.0, 0.0)

    def test_holds_given_components(self):
        v = Vector2D(3.0, -4.0)

        assert (v.x, v.y) == (3.0, -4.0)


class TestArithmetic:
    def test_add(self):
        assert Vector2D(4.0, 5.0) + Vector2D(-1.0, 7.0) == Vector2D(3.0, 12.0)

    def test_sub(self):
        assert Vector2D(4.0, 5.0) - Vector2D(-1.0, 7.0) == Vector2D(5.0, -2.0)

    def test_mul_by_scalar(self):
        assert Vector2D(3.0, -2.0) * 2.0 == Vector2D(6.0, -4.0)

    def test_rmul_matches_mul(self):
        # 2 * v precisa valer o mesmo que v * 2, senao a ordem dos
        # operandos vira uma pegadinha silenciosa no codigo de jogo.
        v = Vector2D(3.0, -2.0)

        assert 2.0 * v == v * 2.0

    def test_truediv_by_scalar(self):
        assert Vector2D(6.0, -4.0) / 2.0 == Vector2D(3.0, -2.0)

    def test_truediv_by_zero_raises(self):
        with pytest.raises(ZeroDivisionError):
            Vector2D(1.0, 1.0) / 0.0

    def test_operators_do_not_mutate_operands(self):
        # Vector2D e mutavel (slots, sem frozen). Se algum operador
        # escrevesse no proprio objeto, um `a + b` dentro do laco de
        # update corromperia `a` em silencio.
        a = Vector2D(1.0, 2.0)
        b = Vector2D(3.0, 4.0)

        a + b
        a - b
        a * 2.0
        a / 2.0

        assert a == Vector2D(1.0, 2.0)
        assert b == Vector2D(3.0, 4.0)


class TestMagnitude:
    def test_magnitude(self):
        assert Vector2D(3.0, 4.0).magnitude() == 5.0

    def test_magnitude_of_origin_is_zero(self):
        assert Vector2D().magnitude() == 0.0

    def test_normalized_has_unit_length(self):
        assert Vector2D(3.0, 4.0).normalized().magnitude() == pytest.approx(
            1.0
        )

    def test_normalized_keeps_direction(self):
        assert Vector2D(3.0, 4.0).normalized() == Vector2D(0.6, 0.8)

    def test_normalized_of_origin_is_origin(self):
        # Sem esta guarda o vetor nulo viraria divisao por zero. E o
        # caso real de "inimigo exatamente em cima do alvo".
        assert Vector2D().normalized() == Vector2D(0.0, 0.0)


class TestRotated:
    def test_rotating_by_zero_changes_nothing(self):
        assert Vector2D(3.0, 4.0).rotated(0.0) == Vector2D(3.0, 4.0)

    def test_quarter_turn_maps_x_onto_y(self):
        # Anti-horario no plano matematico. Com o Y da tela crescendo
        # para baixo, isto aparece como giro horario -- e a convencao.
        rotated = Vector2D(1.0, 0.0).rotated(math.pi / 2.0)

        assert rotated.x == pytest.approx(0.0, abs=1e-9)
        assert rotated.y == pytest.approx(1.0)

    def test_half_turn_negates(self):
        rotated = Vector2D(3.0, 4.0).rotated(math.pi)

        assert rotated.x == pytest.approx(-3.0)
        assert rotated.y == pytest.approx(-4.0)

    def test_full_turn_returns_to_the_start(self):
        rotated = Vector2D(3.0, 4.0).rotated(2.0 * math.pi)

        assert rotated.x == pytest.approx(3.0)
        assert rotated.y == pytest.approx(4.0)

    def test_rotation_preserves_magnitude(self):
        # Rotacao e rigida: se o comprimento mudasse, girar um no
        # esticaria a arvore inteira abaixo dele.
        original = Vector2D(3.0, 4.0)

        rotated = original.rotated(0.7)

        assert rotated.magnitude() == pytest.approx(original.magnitude())

    def test_rotating_the_origin_is_a_no_op(self):
        assert Vector2D().rotated(1.23) == Vector2D(0.0, 0.0)

    def test_does_not_mutate_the_original(self):
        v = Vector2D(3.0, 4.0)

        v.rotated(math.pi)

        assert v == Vector2D(3.0, 4.0)


class TestScaled:
    def test_multiplies_component_by_component(self):
        result = Vector2D(3.0, 4.0).scaled(Vector2D(2.0, 10.0))

        assert result == Vector2D(6.0, 40.0)

    def test_unit_scale_changes_nothing(self):
        assert Vector2D(3.0, 4.0).scaled(Vector2D(1.0, 1.0)) == Vector2D(
            3.0, 4.0
        )

    def test_differs_from_scalar_multiplication(self):
        # E a razao de ser um metodo nomeado e nao uma sobrecarga de
        # __mul__: escala nao-uniforme nao e multiplicacao por escalar.
        v = Vector2D(3.0, 4.0)

        assert v.scaled(Vector2D(2.0, 5.0)) != v * 2.0

    def test_zero_scale_collapses_to_the_origin(self):
        assert Vector2D(3.0, 4.0).scaled(Vector2D()) == Vector2D(0.0, 0.0)

    def test_does_not_mutate_either_operand(self):
        v = Vector2D(3.0, 4.0)
        factors = Vector2D(2.0, 5.0)

        v.scaled(factors)

        assert v == Vector2D(3.0, 4.0)
        assert factors == Vector2D(2.0, 5.0)


class TestProducts:
    def test_dot(self):
        assert Vector2D(1.0, 2.0).dot(Vector2D(3.0, 4.0)) == 11.0

    def test_dot_of_perpendicular_is_zero(self):
        assert Vector2D(1.0, 0.0).dot(Vector2D(0.0, 1.0)) == 0.0

    def test_distance_to(self):
        assert Vector2D(0.0, 0.0).distance_to(Vector2D(3.0, 4.0)) == 5.0

    def test_distance_is_symmetric(self):
        a = Vector2D(1.0, 2.0)
        b = Vector2D(-3.0, 7.0)

        assert a.distance_to(b) == b.distance_to(a)


class TestImmutability:
    """O que substituiu o antigo `copy()`.

    Nao ha o que copiar de um valor imutavel, entao o metodo deixou de
    existir. O que precisa ser garantido agora e o que ele defendia:
    que compartilhar um vetor nao amarra dois donos.
    """

    def test_components_cannot_be_written(self):
        v = Vector2D(1.5, -2.5)

        with pytest.raises(dataclasses.FrozenInstanceError):
            v.x = 99.0  # type: ignore[misc]

    def test_sharing_a_vector_does_not_link_two_owners(self):
        # A linha que o vetor mutavel tornava perigosa. Com valor, ela
        # e so uma leitura.
        shared = Vector2D(10.0, 20.0)
        a = Transform(position=shared)
        b = Transform(position=shared)

        a.position = a.position + Vector2D(5.0, 0.0)

        assert b.position == Vector2D(10.0, 20.0)

    def test_operations_never_touch_the_operand(self):
        v = Vector2D(3.0, 4.0)

        v + Vector2D(1.0, 1.0)
        v * 10.0
        v.rotated(1.5)
        v.normalized()
        v.scaled(Vector2D(2.0, 2.0))

        assert v == Vector2D(3.0, 4.0)

    def test_is_hashable(self):
        # Consequencia util: serve de chave e de membro de conjunto.
        # Enquanto era mutavel, nao servia para nenhum dos dois.
        assert len({Vector2D(1.0, 2.0), Vector2D(1.0, 2.0)}) == 1
        assert {Vector2D(0.0, 0.0): "origem"}[Vector2D(0.0, 0.0)] == "origem"

    def test_copy_is_gone(self):
        # Trava a remocao: reintroduzir o metodo convidaria de volta o
        # estilo defensivo que a imutabilidade tornou desnecessario.
        assert not hasattr(Vector2D(0.0, 0.0), "copy")


class TestFloatEquality:
    def test_equality_is_exact_and_bites_on_accumulation(self):
        # Documenta uma armadilha real, nao um bug do Vector2D: o
        # __eq__ gerado pelo dataclass compara float por igualdade
        # exata. Somar 0.1 dez vezes NAO da 1.0.
        v = Vector2D()

        for _ in range(10):
            v = v + Vector2D(0.1, 0.0)

        assert v != Vector2D(1.0, 0.0)
        assert v.x == pytest.approx(1.0)

    def test_approx_is_the_way_to_compare_computed_vectors(self):
        v = Vector2D(math.sqrt(2.0), math.sqrt(2.0)).normalized()

        assert v.x == pytest.approx(0.7071067811865476)
        assert v.y == pytest.approx(0.7071067811865476)
