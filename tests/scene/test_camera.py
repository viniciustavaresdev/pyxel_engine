import math

import pytest

from engine.math.vector2d import Vector2D
from engine.scene.camera import Camera
from engine.scene.node import Node
from engine.scene.scene import Scene
from engine.scene.visual_node import VisualNode
from tests.conftest import SpyNode, SpyPointer


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


class TestScreenToWorld:
    """A conversao que a mira usa.

    O ponteiro responde em coordenadas de TELA e o jogo precisa do
    alvo em MUNDO. Quem sabe converter e a camera, porque o
    deslocamento e dela.
    """

    def test_the_top_left_of_the_screen_is_the_view_offset(self):
        # A ancora da conversao: tela (0,0) e, por definicao, o canto
        # que `get_view_offset` devolve.
        camera = Camera("Cam", viewport_width=160.0, viewport_height=120.0)
        camera.transform.position = Vector2D(500.0, 300.0)

        assert camera.screen_to_world(Vector2D()) == camera.get_view_offset()

    def test_the_center_of_the_screen_is_the_camera_itself(self):
        # O que a semantica de "a posicao da camera e o CENTRO da tela"
        # promete, dito como conversao.
        camera = Camera("Cam", viewport_width=160.0, viewport_height=120.0)
        camera.transform.position = Vector2D(500.0, 300.0)

        center = Vector2D(80.0, 60.0)

        assert camera.screen_to_world(center) == Vector2D(500.0, 300.0)

    def test_a_camera_at_the_origin_leaves_half_a_screen_of_offset(self):
        camera = Camera("Cam", viewport_width=160.0, viewport_height=120.0)

        assert camera.screen_to_world(Vector2D()) == Vector2D(-80.0, -60.0)

    def test_without_a_viewport_the_offset_is_the_position(self):
        camera = Camera("Cam")
        camera.transform.position = Vector2D(30.0, 40.0)

        assert camera.screen_to_world(Vector2D(5.0, 5.0)) == Vector2D(
            35.0, 45.0
        )

    def test_it_follows_the_camera_through_the_hierarchy(self):
        # O caso do jogo: a camera pendurada no jogador. A conversao sai
        # da transform MUNDIAL, entao mover o jogador move o alvo junto
        # sem uma linha de codigo aqui.
        player = Node("Player")
        camera = Camera("Cam", viewport_width=160.0, viewport_height=120.0)
        player.add_child(camera)
        player.transform.position = Vector2D(500.0, 300.0)

        assert camera.screen_to_world(Vector2D(80.0, 60.0)) == Vector2D(
            500.0, 300.0
        )

    def test_a_cursor_outside_the_screen_still_converts(self):
        # O ponteiro devolve negativo quando o mouse sai pela esquerda.
        # Recortar aqui seria a camera decidindo regra de jogo.
        camera = Camera("Cam", viewport_width=160.0, viewport_height=120.0)
        camera.transform.position = Vector2D(500.0, 300.0)

        assert camera.screen_to_world(Vector2D(-10.0, 200.0)) == Vector2D(
            410.0, 440.0
        )


class TestWorldToScreen:
    def test_the_camera_position_lands_at_the_center_of_the_screen(self):
        camera = Camera("Cam", viewport_width=160.0, viewport_height=120.0)
        camera.transform.position = Vector2D(500.0, 300.0)

        assert camera.world_to_screen(Vector2D(500.0, 300.0)) == Vector2D(
            80.0, 60.0
        )

    def test_a_point_behind_the_camera_goes_negative(self):
        # Util para quem desenha marcador de alvo fora do enquadramento:
        # o sinal e a informacao de que saiu pela borda.
        camera = Camera("Cam", viewport_width=160.0, viewport_height=120.0)
        camera.transform.position = Vector2D(500.0, 300.0)

        assert camera.world_to_screen(Vector2D(400.0, 300.0)) == Vector2D(
            -20.0, 60.0
        )


class TestTheTwoConversionsAreInverses:
    """O contrato que amarra as duas, para vários offsets de camera.

    Uma conversao sozinha pode estar errada e parecer certa -- basta o
    teste repetir a mesma conta que a implementacao faz. Duas que se
    desfazem nao tem esse escape.
    """

    OFFSETS = [
        Vector2D(0.0, 0.0),
        Vector2D(500.0, 300.0),
        Vector2D(-120.0, -45.0),
        Vector2D(0.5, -0.25),
        Vector2D(10000.0, 10000.0),
    ]

    POINTS = [
        Vector2D(0.0, 0.0),
        Vector2D(80.0, 60.0),
        Vector2D(159.0, 119.0),
        Vector2D(-30.0, 400.0),
        Vector2D(7.5, 3.25),
    ]

    @pytest.mark.parametrize("offset", OFFSETS)
    @pytest.mark.parametrize("point", POINTS)
    def test_screen_survives_the_round_trip(self, offset, point):
        camera = Camera("Cam", viewport_width=160.0, viewport_height=120.0)
        camera.transform.position = offset

        assert camera.world_to_screen(camera.screen_to_world(point)) == point

    @pytest.mark.parametrize("offset", OFFSETS)
    @pytest.mark.parametrize("point", POINTS)
    def test_world_survives_the_round_trip(self, offset, point):
        camera = Camera("Cam", viewport_width=160.0, viewport_height=120.0)
        camera.transform.position = offset

        assert camera.screen_to_world(camera.world_to_screen(point)) == point

    def test_it_holds_with_the_camera_deep_in_a_hierarchy(self):
        root = Node("Root")
        player = Node("Player")
        camera = Camera("Cam", viewport_width=160.0, viewport_height=120.0)
        root.add_child(player)
        player.add_child(camera)

        root.transform.position = Vector2D(1000.0, 500.0)
        player.transform.position = Vector2D(33.0, -17.0)
        camera.transform.position = Vector2D(20.0, 0.0)

        point = Vector2D(12.0, 90.0)

        assert camera.world_to_screen(camera.screen_to_world(point)) == point


class TestTheConversionAgreesWithWhatTheRendererDraws:
    """A conversao e a inversa do ENQUADRAMENTO, e nao de uma camera
    ideal.

    A porta enquadra com `set_camera(offset)` -- translacao e nada
    mais. Um teste que so conferisse a aritmetica passaria mesmo que a
    conta discordasse do que aparece na tela; este pergunta ao
    renderer.
    """

    class Blob(VisualNode):
        def on_render(self, renderer):
            bounds = self.get_world_bounds()
            renderer.draw_rect(bounds.position, bounds.size, 7)

    def _render(self, renderer, world_position):
        scene = Scene("Level1")
        camera = Camera("Cam", viewport_width=160.0, viewport_height=120.0)
        camera.transform.position = Vector2D(500.0, 300.0)
        scene.world.add_child(camera)
        scene.camera = camera

        blob = self.Blob("Blob", size=Vector2D(8.0, 8.0))
        blob.transform.position = world_position
        scene.world.add_child(blob)

        scene.render(renderer)

        return camera

    def test_the_drawn_position_minus_the_offset_is_world_to_screen(
        self, renderer
    ):
        camera = self._render(renderer, Vector2D(520.0, 310.0))

        _, offset_x, offset_y = renderer.calls[0]
        _, drawn_x, drawn_y, *_ = renderer.calls[1]

        on_screen = Vector2D(drawn_x - offset_x, drawn_y - offset_y)

        assert camera.world_to_screen(Vector2D(516.0, 306.0)) == on_screen

    def test_a_click_at_the_center_finds_the_node_under_it(self, renderer):
        # O caminho inteiro da semana 1, em um teste: cursor -> tela ->
        # mundo -> a caixa de um no. Se o sinal da conversao estivesse
        # invertido, o alvo cairia do outro lado da camera e este teste
        # seria o unico a notar.
        camera = self._render(renderer, Vector2D(500.0, 300.0))
        pointer = SpyPointer()

        pointer.move_to(80.0, 60.0)
        target = camera.screen_to_world(pointer.get_position())

        blob_bounds = Vector2D(496.0, 296.0)

        assert target == Vector2D(500.0, 300.0)
        assert blob_bounds.x <= target.x < blob_bounds.x + 8.0
        assert blob_bounds.y <= target.y < blob_bounds.y + 8.0


class TestFramingIsTranslationOnly:
    """A limitacao, dita em teste em vez de so no comentario.

    Girar ou escalar o no da camera NAO gira nem escala a vista: a
    porta so aceita um offset. A conversao conta a mesma verdade que o
    desenho, e e isso que a mantem honesta.
    """

    def test_rotating_the_camera_does_not_rotate_the_conversion(self):
        camera = Camera("Cam", viewport_width=160.0, viewport_height=120.0)
        camera.transform.position = Vector2D(500.0, 300.0)

        before = camera.screen_to_world(Vector2D(0.0, 0.0))
        camera.transform.rotation = math.pi / 2.0

        assert camera.screen_to_world(Vector2D(0.0, 0.0)) == before

    def test_scaling_the_camera_does_not_zoom_the_conversion(self):
        camera = Camera("Cam", viewport_width=160.0, viewport_height=120.0)
        camera.transform.position = Vector2D(500.0, 300.0)

        before = camera.screen_to_world(Vector2D(40.0, 30.0))
        camera.transform.scale = Vector2D(2.0, 2.0)

        assert camera.screen_to_world(Vector2D(40.0, 30.0)) == before

    def test_a_rotating_parent_still_moves_the_view(self):
        # O que a rotacao do PAI faz e mover a camera pelo mundo, e isso
        # a conversao acompanha -- e a posicao mundial que entra na
        # conta, e ela girou junto.
        player = Node("Player")
        camera = Camera("Cam")
        camera.transform.position = Vector2D(10.0, 0.0)
        player.add_child(camera)

        player.transform.rotation = math.pi / 2.0
        target = camera.screen_to_world(Vector2D())

        assert target.x == pytest.approx(0.0, abs=1e-9)
        assert target.y == pytest.approx(10.0, abs=1e-9)


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
        scene.update(spy_input)
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
