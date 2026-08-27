from engine.math.vector2d import Vector2D
from engine.scene.camera import Camera
from engine.scene.node import Node
from engine.scene.scene import Scene
from tests.conftest import SpyNode


class TestCameraIsANode:

    def test_inherits_from_node(self):
        assert isinstance(Camera("Cam"), Node)

    def test_can_be_parented(self):
        player = Node("Player")
        camera = Camera("Cam")

        player.add_child(camera)

        assert camera.parent is player


class TestViewOffset:

    def test_without_viewport_the_offset_is_the_position(self):
        # Viewport zerado: a semantica vira "canto superior esquerdo",
        # util para camera presa a uma grade de tiles.
        camera = Camera("Cam")
        camera.transform.position = Vector2D(30.0, 40.0)

        assert camera.get_view_offset() == Vector2D(30.0, 40.0)

    def test_with_viewport_the_position_is_the_center(self):
        camera = Camera("Cam", viewport_width=160.0, viewport_height=120.0)
        camera.transform.position = Vector2D(100.0, 100.0)

        assert camera.get_view_offset() == Vector2D(20.0, 40.0)

    def test_at_the_origin_the_offset_is_half_a_screen_back(self):
        camera = Camera("Cam", viewport_width=160.0, viewport_height=120.0)

        assert camera.get_view_offset() == Vector2D(-80.0, -60.0)

    def test_follows_its_parent_through_the_world_transform(self):
        # O motivo de a Camera ser um Node: pendurada no jogador, ela
        # o segue sem uma linha de codigo de "follow".
        player = Node("Player")
        camera = Camera("Cam", viewport_width=160.0, viewport_height=120.0)
        player.add_child(camera)

        player.transform.position = Vector2D(500.0, 300.0)

        assert camera.get_view_offset() == Vector2D(420.0, 240.0)

    def test_a_local_offset_frames_ahead_of_the_parent(self):
        # Deslocar a camera dentro do pai e como olhar adiante do
        # jogador, sem mover o jogador.
        player = Node("Player")
        camera = Camera("Cam")
        camera.transform.position = Vector2D(20.0, 0.0)
        player.add_child(camera)

        player.transform.position = Vector2D(100.0, 100.0)

        assert camera.get_view_offset() == Vector2D(120.0, 100.0)


class TestSceneCamera:

    def test_a_scene_without_a_camera_draws_in_screen_space(
        self, log, renderer
    ):
        scene = Scene("Level1")
        scene.add_child(SpyNode("Child", log))

        scene.render(renderer)

        assert renderer.calls == [("reset_camera",)]

    def test_a_scene_with_a_camera_offsets_the_view(self, log, renderer):
        scene = Scene("Level1")
        camera = Camera("Cam")
        camera.transform.position = Vector2D(30.0, 40.0)
        scene.add_child(camera)
        scene.camera = camera

        scene.render(renderer)

        assert renderer.calls[0] == ("set_camera", 30.0, 40.0)

    def test_the_camera_is_applied_before_anything_draws(self, log, renderer):
        # Se fosse aplicada num on_render qualquer, bastaria reordenar
        # os filhos para metade da cena sair com o enquadramento errado.
        class Drawer(Node):
            def on_render(self, renderer):
                renderer.draw_rect(Vector2D(0.0, 0.0), Vector2D(1.0, 1.0), 7)

        scene = Scene("Level1")
        camera = Camera("Cam")
        scene.add_child(Drawer("Drawer"))
        scene.add_child(camera)
        scene.camera = camera

        scene.render(renderer)

        assert renderer.calls[0][0] == "set_camera"

    def test_swapping_the_camera_changes_the_framing(self, renderer):
        scene = Scene("Level1")
        near = Camera("Near")
        far = Camera("Far")
        far.transform.position = Vector2D(500.0, 0.0)
        scene.add_child(near)
        scene.add_child(far)

        scene.camera = near
        scene.render(renderer)
        scene.camera = far
        scene.render(renderer)

        assert renderer.calls == [
            ("set_camera", 0.0, 0.0),
            ("set_camera", 500.0, 0.0),
        ]

    def test_clearing_the_camera_returns_to_screen_space(self, renderer):
        scene = Scene("Level1")
        camera = Camera("Cam")
        scene.add_child(camera)
        scene.camera = camera
        scene.render(renderer)
        renderer.calls.clear()

        scene.camera = None
        scene.render(renderer)

        assert renderer.calls == [("reset_camera",)]

    def test_an_invisible_scene_still_sets_the_camera(self, renderer):
        # A camera e enquadramento, nao desenho: aplica-la antes do
        # gate de visibilidade evita que o proximo frame herde o
        # enquadramento do anterior.
        scene = Scene("Level1")
        camera = Camera("Cam")
        camera.transform.position = Vector2D(10.0, 20.0)
        scene.add_child(camera)
        scene.camera = camera
        scene.visible = False

        scene.render(renderer)

        assert renderer.calls == [("set_camera", 10.0, 20.0)]


class TestAnOrphanedCameraStopsFraming:
    """A cena guarda uma referencia forte que ninguem limpa.

    Sem guarda, uma camera arrancada da arvore continuaria enquadrando
    a partir da propria transform LOCAL -- porque `parent` virou None
    -- e a vista saltaria para outro canto do mundo sem erro nenhum.
    """

    def test_a_removed_camera_falls_back_to_screen_space(self, renderer):
        scene = Scene("Level1")
        camera = Camera("Cam")
        camera.transform.position = Vector2D(300.0, 200.0)
        scene.add_child(camera)
        scene.camera = camera

        scene.remove_child(camera)
        scene.render(renderer)

        assert renderer.calls == [("reset_camera",)]

    def test_a_queue_freed_camera_falls_back_after_the_collection(
        self, renderer, spy_input
    ):
        scene = Scene("Level1")
        camera = Camera("Cam")
        camera.transform.position = Vector2D(300.0, 200.0)
        scene.add_child(camera)
        scene.camera = camera

        camera.queue_free()
        scene.update(0.016, spy_input)
        scene.render(renderer)

        assert renderer.calls == [("reset_camera",)]

    def test_a_camera_hanging_on_a_removed_branch_also_stops(self, renderer):
        # A camera nao foi tocada: quem saiu foi o pai dela. O teste que
        # `is_inside_tree` sozinho nao pegaria numa cena nunca entrada.
        scene = Scene("Level1")
        player = Node("Player")
        camera = Camera("Cam")
        player.add_child(camera)
        scene.add_child(player)
        scene.camera = camera

        scene.remove_child(player)
        scene.render(renderer)

        assert renderer.calls == [("reset_camera",)]

    def test_a_camera_from_another_scene_does_not_frame_this_one(
        self, renderer
    ):
        here = Scene("Here")
        elsewhere = Scene("Elsewhere")
        camera = Camera("Cam")
        camera.transform.position = Vector2D(900.0, 900.0)
        elsewhere.add_child(camera)

        here.camera = camera
        here.render(renderer)

        assert renderer.calls == [("reset_camera",)]

    def test_a_camera_put_back_frames_again(self, renderer):
        # A guarda le a arvore a cada frame, entao readotar a camera
        # basta -- nao ha marca a limpar.
        scene = Scene("Level1")
        camera = Camera("Cam")
        camera.transform.position = Vector2D(30.0, 40.0)
        scene.add_child(camera)
        scene.camera = camera

        scene.remove_child(camera)
        scene.add_child(camera)
        scene.render(renderer)

        assert renderer.calls[0] == ("set_camera", 30.0, 40.0)

    def test_the_scene_still_reports_the_camera_it_was_given(self):
        # A guarda mascara a camera para o RENDER; a atribuicao em si
        # continua valendo, e voltar a pendura-la na arvore a revive.
        scene = Scene("Level1")
        camera = Camera("Cam")
        scene.add_child(camera)
        scene.camera = camera
        scene.remove_child(camera)

        assert scene.camera is None

        scene.add_child(camera)

        assert scene.camera is camera

    def test_a_nested_scene_keeps_its_own_camera(self, renderer):
        # Scene e um Node, entao cena dentro de cena e possivel. A
        # guarda pergunta por ascendencia e nao por raiz justamente
        # para nao mascarar a camera da cena de dentro.
        outer = Scene("Outer")
        inner = Scene("Inner")
        camera = Camera("Cam")
        camera.transform.position = Vector2D(70.0, 80.0)
        inner.add_child(camera)
        inner.camera = camera
        outer.add_child(inner)

        inner.render(renderer)

        assert renderer.calls[0] == ("set_camera", 70.0, 80.0)
