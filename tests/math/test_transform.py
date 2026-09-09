import math

import pytest

from engine.math.transform import Transform
from engine.math.vector2d import Vector2D


class TestDefaults:
    def test_starts_at_origin(self):
        assert Transform().position == Vector2D(0.0, 0.0)

    def test_starts_unrotated(self):
        assert Transform().rotation == 0.0

    def test_starts_at_unit_scale(self):
        # Escala default 1 e nao 0 -- caso contrario todo no criado sem
        # argumentos nasceria invisivel assim que a escala for aplicada
        # de fato no render.
        assert Transform().scale == Vector2D(1.0, 1.0)


class TestSharedDefaultsAreSafe:
    """Os defaults deixaram de precisar de default_factory.

    Enquanto Vector2D era mutavel, dois Transform recem-criados nao
    podiam compartilhar a mesma instancia de (0, 0): escrever nela
    moveria todos os nos de uma vez, e a fabrica existia so para
    impedir isso. Com valor imutavel o compartilhamento e inofensivo,
    e o que resta a garantir e que escrever em um nao afeta o outro.
    """

    def test_moving_one_transform_leaves_the_other_alone(self):
        a = Transform()
        b = Transform()

        a.position = Vector2D(99.0, 99.0)

        assert b.position == Vector2D(0.0, 0.0)

    def test_scaling_one_transform_leaves_the_other_alone(self):
        a = Transform()
        b = Transform()

        a.scale = Vector2D(99.0, 99.0)

        assert b.scale == Vector2D(1.0, 1.0)

    def test_the_transform_itself_is_still_mutable(self):
        # De proposito: `no.transform.rotation += x` e a ergonomia que
        # se espera de um no de jogo. So os VALORES que ele guarda e
        # que sao congelados.
        transform = Transform()

        transform.rotation += 0.5

        assert transform.rotation == 0.5


class TestExplicitConstruction:
    def test_accepts_positional_arguments(self):
        transform = Transform(
            Vector2D(0.0, 0.7),
            0.4,
            Vector2D(2.0, 2.0),
        )

        assert transform.position == Vector2D(0.0, 0.7)
        assert transform.rotation == 0.4
        assert transform.scale == Vector2D(2.0, 2.0)

    def test_fields_are_writable(self):
        transform = Transform()

        transform.position = Vector2D(10.0, 20.0)
        transform.rotation = 1.5

        assert transform.position == Vector2D(10.0, 20.0)
        assert transform.rotation == 1.5


class TestCopy:
    def test_copy_is_equal(self):
        original = Transform(Vector2D(1.0, 2.0), 0.5, Vector2D(3.0, 4.0))

        assert original.copy() == original

    def test_writing_to_the_copy_does_not_reach_the_original(self):
        # A copia continua sendo necessaria porque o TRANSFORM e
        # mutavel -- mesmo com os campos imutaveis, os dois objetos
        # precisam ser distintos.
        original = Transform(Vector2D(1.0, 2.0))

        clone = original.copy()
        clone.position = Vector2D(99.0, 99.0)
        clone.scale = Vector2D(99.0, 99.0)

        assert original.position == Vector2D(1.0, 2.0)
        assert original.scale == Vector2D(1.0, 1.0)

    def test_the_copy_is_a_distinct_object(self):
        original = Transform(Vector2D(1.0, 2.0))

        assert original.copy() is not original


class TestCompose:
    """`pai.compose(local)` devolve a transform mundial do filho."""

    def test_identity_parent_yields_the_local_transform(self):
        local = Transform(Vector2D(10.0, 20.0), 0.5, Vector2D(2.0, 3.0))

        assert Transform().compose(local) == local

    def test_identity_local_yields_the_parent_transform(self):
        parent = Transform(Vector2D(10.0, 20.0), 0.5, Vector2D(2.0, 3.0))

        assert parent.compose(Transform()) == parent

    def test_translations_add_up(self):
        parent = Transform(Vector2D(10.0, 20.0))
        local = Transform(Vector2D(1.0, 2.0))

        assert parent.compose(local).position == Vector2D(11.0, 22.0)

    def test_rotations_add_up(self):
        parent = Transform(rotation=0.3)
        local = Transform(rotation=0.4)

        assert parent.compose(local).rotation == pytest.approx(0.7)

    def test_scales_multiply(self):
        parent = Transform(scale=Vector2D(2.0, 3.0))
        local = Transform(scale=Vector2D(4.0, 5.0))

        assert parent.compose(local).scale == Vector2D(8.0, 15.0)

    def test_parent_scale_stretches_the_local_offset(self):
        parent = Transform(scale=Vector2D(2.0, 2.0))
        local = Transform(Vector2D(10.0, 0.0))

        assert parent.compose(local).position == Vector2D(20.0, 0.0)

    def test_parent_rotation_orbits_the_local_offset(self):
        parent = Transform(rotation=math.pi / 2.0)
        local = Transform(Vector2D(10.0, 0.0))

        position = parent.compose(local).position

        assert position.x == pytest.approx(0.0, abs=1e-9)
        assert position.y == pytest.approx(10.0)

    def test_scale_runs_before_rotation(self):
        # Ordem escala -> rotacao -> translacao. Se a rotacao viesse
        # primeiro, o offset seria esticado no eixo ja girado e daria
        # (0, 10) em vez de (0, 30).
        parent = Transform(rotation=math.pi / 2.0, scale=Vector2D(3.0, 1.0))
        local = Transform(Vector2D(10.0, 0.0))

        position = parent.compose(local).position

        assert position.x == pytest.approx(0.0, abs=1e-9)
        assert position.y == pytest.approx(30.0)

    def test_local_rotation_does_not_move_the_local_offset(self):
        # O filho gira em torno do proprio eixo sem sair do lugar; quem
        # o desloca e a rotacao do PAI.
        parent = Transform()
        local = Transform(Vector2D(10.0, 0.0), math.pi)

        assert parent.compose(local).position == Vector2D(10.0, 0.0)

    def test_does_not_mutate_either_operand(self):
        parent = Transform(Vector2D(10.0, 20.0), 0.5, Vector2D(2.0, 2.0))
        local = Transform(Vector2D(1.0, 2.0), 0.25, Vector2D(3.0, 3.0))

        parent.compose(local)

        assert parent == Transform(
            Vector2D(10.0, 20.0), 0.5, Vector2D(2.0, 2.0)
        )
        assert local == Transform(Vector2D(1.0, 2.0), 0.25, Vector2D(3.0, 3.0))

    def test_composing_left_to_right_matches_a_three_level_chain(self):
        # Associatividade: (avo . pai) . filho == avo . (pai . filho).
        # E o que garante que get_world_transform pode subir a cadeia
        # em qualquer ordem e dar o mesmo resultado.
        grandparent = Transform(Vector2D(5.0, 0.0), 0.3, Vector2D(2.0, 2.0))
        parent = Transform(Vector2D(1.0, 1.0), 0.2, Vector2D(1.5, 1.5))
        child = Transform(Vector2D(2.0, 3.0), 0.1, Vector2D(0.5, 0.5))

        left = grandparent.compose(parent).compose(child)
        right = grandparent.compose(parent.compose(child))

        assert left.position.x == pytest.approx(right.position.x)
        assert left.position.y == pytest.approx(right.position.y)
        assert left.rotation == pytest.approx(right.rotation)
        assert left.scale.x == pytest.approx(right.scale.x)


class TestChangeHook:
    """O gancho que torna o cache de transform mundial possivel.

    Daqui de dentro ele e opaco: um Callable que alguem pendurou para
    ser avisado. O `math/` continua sem saber que existe arvore de
    cena -- quem sabe e o Node, que pendura o proprio invalidador.
    """

    def test_a_fresh_transform_notifies_nobody(self):
        # E o que faz compose() e copy() serem baratos: o caminho de
        # render constroi um Transform por no por nivel, e nenhum deles
        # pertence a ninguem.
        assert Transform()._on_change is None

    def test_writing_a_field_calls_the_hook(self):
        calls = []
        transform = Transform()
        transform._on_change = lambda: calls.append(1)

        transform.position = Vector2D(1.0, 0.0)
        transform.rotation = 0.5
        transform.scale = Vector2D(2.0, 2.0)

        assert len(calls) == 3

    def test_writing_the_same_value_does_not_call_the_hook(self):
        calls = []
        transform = Transform(Vector2D(1.0, 2.0), 0.5, Vector2D(3.0, 3.0))
        transform._on_change = lambda: calls.append(1)

        transform.position = Vector2D(1.0, 2.0)
        transform.rotation = 0.5
        transform.scale = Vector2D(3.0, 3.0)

        assert calls == []

    def test_the_value_is_written_before_the_hook_runs(self):
        # O invalidador do Node nao le o transform, mas um observador
        # que lesse precisa ver o valor NOVO -- avisar antes de
        # escrever seria avisar sobre um estado que nao existe.
        seen = []
        transform = Transform()
        transform._on_change = lambda: seen.append(transform.rotation)

        transform.rotation = 1.5

        assert seen == [1.5]

    def test_copy_does_not_carry_the_hook(self):
        # A copia e um valor solto, nao o transform local de um no.
        transform = Transform()
        transform._on_change = lambda: None

        assert transform.copy()._on_change is None

    def test_compose_does_not_carry_the_hook(self):
        parent = Transform()
        parent._on_change = lambda: None
        local = Transform()
        local._on_change = lambda: None

        assert parent.compose(local)._on_change is None

    def test_the_hook_is_not_part_of_the_value(self):
        a = Transform(Vector2D(1.0, 2.0))
        b = Transform(Vector2D(1.0, 2.0))
        a._on_change = lambda: None

        assert a == b


class TestValueSemantics:
    """O que o dataclass dava de graca e agora e escrito a mao."""

    def test_equality_is_by_value(self):
        assert Transform(Vector2D(1.0, 2.0), 0.5, Vector2D(3.0, 4.0)) == (
            Transform(Vector2D(1.0, 2.0), 0.5, Vector2D(3.0, 4.0))
        )

    def test_differs_when_any_field_differs(self):
        base = Transform(Vector2D(1.0, 2.0), 0.5, Vector2D(3.0, 4.0))

        assert base != Transform(Vector2D(9.0, 2.0), 0.5, Vector2D(3.0, 4.0))
        assert base != Transform(Vector2D(1.0, 2.0), 9.0, Vector2D(3.0, 4.0))
        assert base != Transform(Vector2D(1.0, 2.0), 0.5, Vector2D(9.0, 4.0))

    def test_comparing_with_something_else_is_not_an_error(self):
        assert Transform() != "not a transform"
        assert Transform() is not None

    def test_is_not_hashable(self):
        # Mutavel, logo nao serve de chave: mudaria de valor debaixo da
        # tabela. Mesma regra que o dataclass aplicava sozinho.
        with pytest.raises(TypeError):
            hash(Transform())

    def test_repr_shows_the_three_fields(self):
        transform = Transform(Vector2D(1.0, 2.0), 0.5, Vector2D(3.0, 4.0))

        assert repr(transform) == (
            "Transform(position=Vector2D(x=1.0, y=2.0), "
            "rotation=0.5, "
            "scale=Vector2D(x=3.0, y=4.0))"
        )

    def test_repr_does_not_leak_the_hook(self):
        transform = Transform()
        transform._on_change = lambda: None

        assert "_on_change" not in repr(transform)
