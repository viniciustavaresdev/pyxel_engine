"""As duas camadas de render da Scene.

O que elas resolvem: antes, um HUD desenhava em espaco de tela chamando
`reset_camera()` de dentro do proprio `on_render` -- estado global do
renderer alterado no meio da travessia, e correto so enquanto aquele no
fosse o ultimo filho. Ninguem declarava essa ordem em lugar nenhum.

Agora quem decide o espaco de cada passada e a cena.
"""

import pytest

from engine.math.vector2d import Vector2D
from engine.scene.camera import Camera
from engine.scene.node import Node
from engine.scene.scene import Scene
from tests.conftest import SpyNode


class Drawer(Node):
    """Desenha um retangulo identificavel pela cor."""

    def __init__(self, name=None, color=7):
        super().__init__(name)
        self.color = color

    def on_render(self, renderer):
        renderer.draw_rect(Vector2D(0.0, 0.0), Vector2D(1.0, 1.0), self.color)


class TestTheLayersAreOrdinaryNodes:
    """Camada e conceito de ORDEM e ESPACO, nao um mecanismo paralelo."""

    def test_both_layers_are_children_of_the_scene(self):
        scene = Scene("Level1")

        assert scene.world.parent is scene
        assert scene.ui.parent is scene

    def test_the_world_layer_comes_first(self):
        # E a ordem de update, alem da de render.
        scene = Scene("Level1")

        assert scene.children.index(scene.world) < scene.children.index(
            scene.ui
        )

    def test_update_reaches_both_layers(self, log, spy_input):
        scene = Scene("Level1")
        scene.world.add_child(SpyNode("InWorld", log))
        scene.ui.add_child(SpyNode("InUi", log))

        scene.update(spy_input)

        assert log == [("update", "InWorld"), ("update", "InUi")]

    def test_enter_reaches_both_layers(self, log):
        scene = Scene("Level1")
        scene.world.add_child(SpyNode("InWorld", log))
        scene.ui.add_child(SpyNode("InUi", log))

        scene.enter()

        assert log == [("enter", "InWorld"), ("enter", "InUi")]

    def test_queue_free_inside_a_layer_is_collected(self, spy_input):
        # A fila mora na raiz, que continua sendo a cena: uma camada no
        # meio do caminho nao muda isso.
        scene = Scene("Level1")
        doomed = Node("Doomed")
        scene.ui.add_child(doomed)
        scene.enter()

        doomed.queue_free()
        scene.update(spy_input)

        assert scene.ui.children == []

    def test_the_layers_are_read_only(self):
        # Trocar a camada por outro no deixaria a antiga pendurada na
        # cena, ainda desenhando, e o render procurando a nova.
        scene = Scene("Level1")

        # O `type: ignore` faz parte do teste: o mypy tambem recusa
        # estas duas linhas. O runtime recusar junto e o que impede a
        # protecao de depender de alguem rodar o checador.
        with pytest.raises(AttributeError):
            scene.world = Node("Other")  # type: ignore[misc]

        with pytest.raises(AttributeError):
            scene.ui = Node("Other")  # type: ignore[misc]


class TestDrawOrder:
    def test_the_ui_layer_draws_after_the_world(self, log, renderer):
        scene = Scene("Level1")
        scene.ui.add_child(SpyNode("InUi", log))
        scene.world.add_child(SpyNode("InWorld", log))

        scene.render(renderer)

        assert log == [("render", "InWorld"), ("render", "InUi")]

    def test_the_ui_draws_last_even_when_added_first(self, log, renderer):
        # O ponto do passo: a ordem nao vem mais da posicao na lista de
        # filhos. O `ui` e criado ANTES de qualquer no de jogo e ainda
        # assim desenha por ultimo.
        scene = Scene("Level1")
        scene.ui.add_child(SpyNode("InUi", log))
        scene.add_child(SpyNode("DirectChild", log))

        scene.render(renderer)

        assert log == [("render", "DirectChild"), ("render", "InUi")]

    def test_a_direct_child_still_draws_in_world_space(self, renderer):
        # Compatibilidade: pendurar direto na cena continua valendo e
        # continua caindo no espaco de mundo.
        scene = Scene("Level1")
        camera = Camera("Cam")
        camera.transform.position = Vector2D(30.0, 40.0)
        scene.world.add_child(camera)
        scene.camera = camera
        scene.add_child(Drawer("Direct", color=7))

        scene.render(renderer)

        assert renderer.calls == [
            ("set_camera", 30.0, 40.0),
            ("draw_rect", 0.0, 0.0, 1.0, 1.0, 7),
        ]


class TestTheSpaceOfEachPass:
    def test_the_world_is_framed_and_the_ui_is_not(self, renderer):
        scene = Scene("Level1")
        camera = Camera("Cam")
        camera.transform.position = Vector2D(100.0, 50.0)
        scene.world.add_child(camera)
        scene.camera = camera
        scene.world.add_child(Drawer("InWorld", color=11))
        scene.ui.add_child(Drawer("InUi", color=8))

        scene.render(renderer)

        assert renderer.calls == [
            ("set_camera", 100.0, 50.0),
            ("draw_rect", 0.0, 0.0, 1.0, 1.0, 11),
            ("reset_camera",),
            ("draw_rect", 0.0, 0.0, 1.0, 1.0, 8),
        ]

    def test_the_reset_comes_from_the_scene_and_not_from_the_node(
        self, renderer
    ):
        # O `Drawer` so desenha: quem sai do enquadramento antes dele e
        # a cena. Era isso que o Hud da demo fazia a mao, e que so
        # estava certo enquanto ele fosse o ultimo filho.
        scene = Scene("Level1")
        camera = Camera("Cam")
        camera.transform.position = Vector2D(30.0, 40.0)
        scene.world.add_child(camera)
        scene.camera = camera
        scene.ui.add_child(Drawer("InUi", color=8))

        scene.render(renderer)

        assert renderer.calls == [
            ("set_camera", 30.0, 40.0),
            ("reset_camera",),
            ("draw_rect", 0.0, 0.0, 1.0, 1.0, 8),
        ]

    def test_the_camera_can_hang_anywhere_in_the_world_layer(self, renderer):
        # A guarda de camera orfa pergunta por ascendencia, entao a
        # camada no meio do caminho nao a mascara.
        scene = Scene("Level1")
        player = Node("Player")
        camera = Camera("Cam", viewport_width=160.0, viewport_height=120.0)
        player.add_child(camera)
        scene.world.add_child(player)
        scene.camera = camera

        player.transform.position = Vector2D(500.0, 300.0)
        scene.render(renderer)

        assert renderer.calls[0] == ("set_camera", 420.0, 240.0)


class TestAnEmptyUiLayerCostsNothing:
    """Uma cena que nao usa UI tem o mesmo trafego de renderer de antes."""

    def test_no_reset_is_emitted_for_an_empty_layer(self, renderer):
        scene = Scene("Level1")
        camera = Camera("Cam")
        scene.world.add_child(camera)
        scene.camera = camera

        scene.render(renderer)

        assert renderer.calls == [("set_camera", 0.0, 0.0)]

    def test_an_invisible_ui_layer_is_skipped_entirely(self, log, renderer):
        scene = Scene("Level1")
        camera = Camera("Cam")
        scene.world.add_child(camera)
        scene.camera = camera
        scene.ui.add_child(SpyNode("InUi", log))
        scene.ui.visible = False

        scene.render(renderer)

        assert renderer.calls == [("set_camera", 0.0, 0.0)]
        assert log == []


class TestThePauseCase:
    """Por que `world` existe, mesmo com filhos diretos ja funcionando."""

    def test_freezing_the_world_keeps_the_ui_alive(self, log, spy_input):
        # Um menu de pausa em uma linha: `scene.world.active = False`.
        scene = Scene("Level1")
        scene.world.add_child(SpyNode("Enemy", log))
        scene.ui.add_child(SpyNode("Menu", log))

        scene.world.active = False
        scene.update(spy_input)

        assert log == [("update", "Menu")]

    def test_a_frozen_world_is_still_drawn(self, log, renderer):
        # Os dois portoes sao separados: pausado continua na tela.
        scene = Scene("Level1")
        scene.world.add_child(SpyNode("Enemy", log))

        scene.world.active = False
        scene.render(renderer)

        assert log == [("render", "Enemy")]

    def test_hiding_the_world_keeps_the_ui_on_screen(self, log, renderer):
        scene = Scene("Level1")
        scene.world.add_child(SpyNode("Enemy", log))
        scene.ui.add_child(SpyNode("Menu", log))

        scene.world.visible = False
        scene.render(renderer)

        assert log == [("render", "Menu")]
