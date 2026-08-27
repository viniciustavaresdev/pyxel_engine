from engine.runtime.application_config import ApplicationConfig
from engine.runtime.clock import Clock
from engine.runtime.engine import Engine
from engine.runtime.game import Game
from engine.scene.node import Node
from engine.scene.scene_manager import SceneManager
from tests.conftest import (
    SpyApplication,
    SpyInput,
    SpyScene,
    SpyTimeProvider,
)


def build_game(log, renderer, frames=1, scene=None, input=None):
    """Game real sobre Engine e SceneManager reais.

    So a Application e o Renderer sao dublados: sao as bordas com o
    mundo externo (janela, desenho). O resto e a fiacao de verdade.
    """
    manager = SceneManager()
    manager.change_scene(
        scene if scene is not None else SpyScene("Level1", log)
    )
    log.clear()

    engine = Engine(
        clock=Clock(SpyTimeProvider()),
        scene_manager=manager,
        renderer=renderer,
        input=input if input is not None else SpyInput(),
    )

    application = SpyApplication(frames=frames)

    game = Game(
        application=application,
        engine=engine,
        config=ApplicationConfig(width=160, height=120, title="Test"),
    )

    return game, application, engine


class TestStartupSequence:

    def test_initializes_the_backend_with_the_config(self, log, renderer):
        game, application, _ = build_game(log, renderer)

        game.run()

        assert application.config == ApplicationConfig(
            width=160, height=120, title="Test"
        )

    def test_initializes_before_running_the_loop(self, log, renderer):
        # Ordem obrigatoria: pyxel.run() sem pyxel.init() nao tem
        # janela para desenhar.
        game, application, _ = build_game(log, renderer)

        game.run()

        assert application.calls[:2] == ["initialize", "run"]

    def test_starts_the_engine(self, log, renderer):
        game, _, engine = build_game(log, renderer)

        game.run()

        assert engine.is_running is True


class TestInitialScene:

    def test_loads_the_initial_scene(self, log, renderer):
        manager = SceneManager()
        engine = Engine(
            clock=Clock(SpyTimeProvider()),
            scene_manager=manager,
            renderer=renderer,
            input=SpyInput(),
        )
        scene = SpyScene("Level1", log)
        game = Game(
            application=SpyApplication(frames=1),
            engine=engine,
            config=ApplicationConfig(width=160, height=120, title="Test"),
            initial_scene=scene,
        )

        game.run()

        assert manager.current_scene is scene

    def test_enters_the_scene_only_after_the_backend_is_up(
        self, log, renderer
    ):
        # A ordem que motivou o initial_scene: uma cena que carrega
        # arte no on_enter precisa dos bancos de imagem ja criados.
        # Antes disto o on_enter rodava antes do pyxel.init().
        events = []

        class RecordingApplication(SpyApplication):
            def initialize(self, config):
                events.append("initialize")
                super().initialize(config)

        class LoudScene(SpyScene):
            def on_enter(self):
                events.append("scene_enter")
                super().on_enter()

        engine = Engine(
            clock=Clock(SpyTimeProvider()),
            scene_manager=SceneManager(),
            renderer=renderer,
            input=SpyInput(),
        )
        game = Game(
            application=RecordingApplication(frames=1),
            engine=engine,
            config=ApplicationConfig(width=160, height=120, title="Test"),
            initial_scene=LoudScene("Level1", log),
        )

        game.run()

        assert events == ["initialize", "scene_enter"]

    def test_runs_without_an_initial_scene(self, renderer):
        # Continua legal nao passar cena: o loop gira contra um
        # SceneManager vazio em vez de explodir.
        engine = Engine(
            clock=Clock(SpyTimeProvider()),
            scene_manager=SceneManager(),
            renderer=renderer,
            input=SpyInput(),
        )
        game = Game(
            application=SpyApplication(frames=2),
            engine=engine,
            config=ApplicationConfig(width=160, height=120, title="Test"),
        )

        game.run()

        assert renderer.calls == [("clear", 0)] * 2


class TestFrameLoop:

    def test_drives_update_and_render_every_frame(self, log, renderer):
        game, _, _ = build_game(log, renderer, frames=3)

        game.run()

        assert (
            log
            == [
                ("update", "Level1", 0.0),
                ("render", "Level1"),
            ]
            * 3
        )

    def test_clears_the_screen_every_frame(self, log, renderer):
        game, _, _ = build_game(log, renderer, frames=3)

        game.run()

        assert renderer.calls == [("clear", 0), ("reset_camera",)] * 3


class TestQuit:

    def test_does_not_quit_while_the_engine_runs(self, log, renderer):
        game, application, _ = build_game(log, renderer, frames=3)

        game.run()

        assert "quit" not in application.calls
        assert application.frames_run == 3

    def test_stopping_the_engine_closes_the_window(self, log, renderer):
        # A regressao que motivou o Application.quit(): antes, parar a
        # Engine so congelava a tela -- update e render viravam no-op e
        # o backend seguia girando.
        class Quitter(Node):
            def __init__(self, name, engine):
                super().__init__(name)
                self.engine = engine

            def on_update(self, dt, input):
                self.engine.stop()

        scene = SpyScene("Level1", log)
        game, application, engine = build_game(
            log, renderer, frames=10, scene=scene
        )
        scene.add_child(Quitter("Quitter", engine))

        game.run()

        assert "quit" in application.calls

    def test_stops_the_loop_on_the_frame_it_quits(self, log, renderer):
        class Quitter(Node):
            def __init__(self, name, engine):
                super().__init__(name)
                self.engine = engine

            def on_update(self, dt, input):
                self.engine.stop()

        scene = SpyScene("Level1", log)
        game, application, engine = build_game(
            log, renderer, frames=10, scene=scene
        )
        scene.add_child(Quitter("Quitter", engine))

        game.run()

        assert application.frames_run == 1
