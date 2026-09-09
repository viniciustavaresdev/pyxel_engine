"""Contrato da porta Pointer, exercido pelo SpyPointer.

O que se verifica aqui e a fronteira: que a porta devolve um Vector2D,
que ela e SEPARADA de Input, e que os botoes do mouse ficaram do outro
lado dessa divisao -- dentro do vocabulario de `Key`. A leitura do
cursor de verdade e do adaptador, e esta em tests/adapters/.
"""

from engine.input.key import Key
from engine.math.vector2d import Vector2D
from engine.ports.input import Input
from engine.ports.pointer import Pointer
from engine.scene.node import Node
from tests.conftest import SpyInput, SpyPointer


class TestTheReportedPosition:
    def test_it_is_a_vector(self, pointer):
        assert isinstance(pointer.get_position(), Vector2D)

    def test_it_starts_at_the_origin(self, pointer):
        assert pointer.get_position() == Vector2D(0.0, 0.0)

    def test_it_follows_the_cursor(self, pointer):
        pointer.move_to(120.0, 45.0)

        assert pointer.get_position() == Vector2D(120.0, 45.0)

    def test_a_second_frame_replaces_the_first(self, pointer):
        pointer.move_to(10.0, 10.0)
        pointer.move_to(11.0, 12.0)

        assert pointer.get_position() == Vector2D(11.0, 12.0)

    def test_a_held_reference_is_not_rewritten_by_a_later_frame(self):
        # O duble devolve a propria instancia, sem copiar. Isso so e
        # seguro porque Vector2D e imutavel: um no que guardasse o alvo
        # de mira do frame passado continuaria vendo o valor que leu.
        pointer = SpyPointer(Vector2D(3.0, 4.0))
        before = pointer.get_position()

        pointer.move_to(99.0, 99.0)

        assert before == Vector2D(3.0, 4.0)


class TestTheDivisionBetweenPositionAndButtons:
    """A decisao que a semana 1 tomou, travada nos dois sentidos."""

    def test_a_pointer_is_not_an_input(self):
        # Posicao e continua e nao tem analogo em teclado. Se um dia
        # `get_position` migrar para dentro de `Input`, este teste cai
        # e a decisao volta a mesa em vez de mudar em silencio.
        assert not isinstance(SpyPointer(), Input)

    def test_an_input_is_not_a_pointer(self):
        assert not isinstance(SpyInput(), Pointer)

    def test_the_mouse_buttons_live_in_the_key_vocabulary(self):
        # O outro lado da divisao: botao E tecla, porque responde as
        # mesmas tres perguntas.
        assert hasattr(Key, "MOUSE_LEFT")
        assert hasattr(Key, "MOUSE_RIGHT")

    def test_a_mouse_button_answers_the_three_input_questions(self):
        input = SpyInput()

        input.press(Key.MOUSE_LEFT)
        assert input.is_pressed(Key.MOUSE_LEFT)
        assert input.is_just_pressed(Key.MOUSE_LEFT)

        input.hold(Key.MOUSE_LEFT)
        assert input.is_pressed(Key.MOUSE_LEFT)
        assert not input.is_just_pressed(Key.MOUSE_LEFT)

        input.release(Key.MOUSE_LEFT)
        assert not input.is_pressed(Key.MOUSE_LEFT)
        assert input.is_just_released(Key.MOUSE_LEFT)


class TestPointerReachesTheGraph:
    def test_a_node_aims_at_the_cursor(self, spy_input, pointer):
        # O ponteiro chega ao no pelo CONSTRUTOR, e nao pela assinatura
        # do on_update. E a mesma escolha do ActionMap: e configuracao
        # do jogo, e acrescenta-lo ao update obrigaria todo no da
        # arvore a carregar um argumento que quase nenhum usa.
        seen = []

        class Aimer(Node):
            def __init__(self, name, pointer):
                super().__init__(name)
                self.pointer = pointer

            def on_update(self, input):
                seen.append(self.pointer.get_position())

        parent = Node("Parent")
        parent.add_child(Aimer("Aimer", pointer))

        pointer.move_to(80.0, 60.0)
        parent.update(spy_input)

        assert seen == [Vector2D(80.0, 60.0)]


class TestPortContract:
    def test_spy_pointer_satisfies_the_port(self):
        assert isinstance(SpyPointer(), Pointer)

    def test_the_port_has_no_unimplemented_methods(self):
        assert Pointer.__abstractmethods__ - set(dir(SpyPointer())) == set()
