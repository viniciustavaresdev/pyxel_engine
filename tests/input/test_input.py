from engine.input.key import Key
from engine.ports.input import Input
from engine.scene.node import Node
from tests.conftest import SpyInput


class TestKey:

    def test_values_are_distinct(self):
        assert len(set(Key)) == len(list(Key))

    def test_covers_the_directional_set(self):
        for name in ("UP", "DOWN", "LEFT", "RIGHT"):
            assert hasattr(Key, name)

    def test_does_not_leak_backend_constants(self):
        # O valor de uma Key nao pode ser o inteiro do Pyxel: se fosse,
        # trocar de backend silenciosamente mudaria o significado das
        # teclas em vez de quebrar o build.
        assert all(isinstance(key.value, int) for key in Key)
        assert {key.value for key in Key} == set(range(1, len(Key) + 1))


class TestSpyInputStates:
    """O duble precisa distinguir os tres estados, senao os testes de
    input viram teatro."""

    def test_press_marks_pressed_and_just_pressed(self):
        input = SpyInput()

        input.press(Key.SPACE)

        assert input.is_pressed(Key.SPACE)
        assert input.is_just_pressed(Key.SPACE)
        assert not input.is_just_released(Key.SPACE)

    def test_hold_keeps_pressed_but_clears_just_pressed(self):
        input = SpyInput()
        input.press(Key.SPACE)

        input.hold(Key.SPACE)

        assert input.is_pressed(Key.SPACE)
        assert not input.is_just_pressed(Key.SPACE)

    def test_release_clears_pressed_and_marks_just_released(self):
        input = SpyInput()
        input.press(Key.SPACE)

        input.release(Key.SPACE)

        assert not input.is_pressed(Key.SPACE)
        assert input.is_just_released(Key.SPACE)

    def test_untouched_keys_are_all_false(self):
        input = SpyInput()
        input.press(Key.SPACE)

        assert not input.is_pressed(Key.ESCAPE)
        assert not input.is_just_pressed(Key.ESCAPE)
        assert not input.is_just_released(Key.ESCAPE)


class TestInputReachesTheGraph:

    def test_the_same_input_reaches_the_leaves(self, spy_input):
        seen = []

        class Reader(Node):
            def on_update(self, dt, input):
                seen.append(input)

        parent = Node("Parent")
        child = Node("Child")
        child.add_child(Reader("Reader"))
        parent.add_child(child)

        parent.update(0.016, spy_input)

        assert seen == [spy_input]

    def test_a_node_reads_a_held_key(self, spy_input):
        moved = []

        class Walker(Node):
            def on_update(self, dt, input):
                if input.is_pressed(Key.RIGHT):
                    moved.append(dt)

        parent = Node("Parent")
        parent.add_child(Walker("Walker"))

        spy_input.press(Key.RIGHT)
        parent.update(0.016, spy_input)
        spy_input.hold(Key.RIGHT)
        parent.update(0.016, spy_input)

        assert moved == [0.016, 0.016]

    def test_just_pressed_fires_once_per_press(self, spy_input):
        # O caso que motiva os tres estados: com is_pressed, o pulo
        # dispararia em todo frame com a tecla baixa.
        jumps = []

        class Jumper(Node):
            def on_update(self, dt, input):
                if input.is_just_pressed(Key.SPACE):
                    jumps.append("jump")

        parent = Node("Parent")
        parent.add_child(Jumper("Jumper"))

        spy_input.press(Key.SPACE)
        parent.update(0.016, spy_input)
        spy_input.hold(Key.SPACE)
        parent.update(0.016, spy_input)
        parent.update(0.016, spy_input)

        assert jumps == ["jump"]

    def test_an_inactive_node_does_not_read_input(self, spy_input):
        seen = []

        class Reader(Node):
            def on_update(self, dt, input):
                seen.append(input)

        parent = Node("Parent")
        reader = Reader("Reader")
        parent.add_child(reader)
        reader.active = False

        parent.update(0.016, spy_input)

        assert seen == []


class TestPortContract:

    def test_spy_input_satisfies_the_port(self):
        assert isinstance(SpyInput(), Input)

    def test_the_port_has_no_unimplemented_methods(self):
        assert Input.__abstractmethods__ - set(dir(SpyInput())) == set()
