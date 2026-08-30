from engine.math.vector2d import Vector2D
from engine.scene.node import Node
from engine.scene.scene import Scene
from tests.conftest import SpyNode


class TestSceneIsANode:

    def test_inherits_from_node(self):
        # Uma Scene ser um Node e o que permite aninhar cena dentro de
        # cena mais tarde. Se isto quebrar, o SceneManager quebra junto.
        assert issubclass(Scene, Node)

    def test_keeps_the_given_name(self):
        assert Scene("Level1").name == "Level1"

    def test_name_is_optional(self):
        assert Scene().name is None

    def test_starts_with_the_two_layers_and_no_parent(self):
        # Nao nasce vazia: as duas camadas de render sao filhas comuns,
        # criadas no construtor. E o que faz update, enter/exit e a fila
        # de remocao valerem para elas sem uma linha nova.
        scene = Scene("Level1")

        assert scene.children == [scene.world, scene.ui]
        assert scene.parent is None

    def test_starts_with_a_default_transform(self):
        scene = Scene("Level1")

        assert scene.transform.position == Vector2D(0.0, 0.0)
        assert scene.transform.scale == Vector2D(1.0, 1.0)


class TestSceneAsGraphRoot:

    def test_propagates_update_to_its_children(self, log, spy_input):
        scene = Scene("Level1")
        scene.add_child(SpyNode("Child", log))

        scene.update(spy_input)

        assert log == [("update", "Child")]

    def test_propagates_render_to_its_children(self, log, renderer):
        scene = Scene("Level1")
        scene.add_child(SpyNode("Child", log))

        scene.render(renderer)

        assert log == [("render", "Child")]

    def test_is_the_origin_of_world_coordinates(self):
        # Cena na origem: a posicao mundial do filho e a local dele.
        scene = Scene("Level1")
        child = Node("Child")
        child.transform.position = Vector2D(30.0, 40.0)
        scene.add_child(child)

        assert child.get_world_position() == Vector2D(30.0, 40.0)

    def test_moving_the_scene_moves_everything_in_it(self):
        # E o que torna scroll de camera possivel sem tocar em cada no.
        scene = Scene("Level1")
        child = Node("Child")
        child.transform.position = Vector2D(30.0, 40.0)
        scene.add_child(child)

        scene.transform.position = Vector2D(-10.0, -10.0)

        assert child.get_world_position() == Vector2D(20.0, 30.0)
