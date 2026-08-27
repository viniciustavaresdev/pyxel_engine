import pytest

from engine.runtime.clock import Clock
from engine.runtime.engine import Engine
from engine.scene.scene_manager import SceneManager
from tests.conftest import SpyInput, SpyScene, SpyTimeProvider


def build_engine(log, renderer, clear_color=0, input=None):
    """Engine real ligada a um SceneManager real e a dubles nas bordas.

    So o tempo, o desenho e o teclado sao dublados: o objetivo e testar
    a fiacao entre Engine, Clock e SceneManager, nao substitui-la por
    mocks.
    """
    time = SpyTimeProvider()
    manager = SceneManager()
    manager.change_scene(SpyScene("Level1", log))
    log.clear()

    engine = Engine(
        clock=Clock(time),
        scene_manager=manager,
        renderer=renderer,
        input=input if input is not None else SpyInput(),
        clear_color=clear_color,
    )

    return engine, time


class TestRunningState:

    def test_starts_stopped(self, log, renderer):
        engine, _ = build_engine(log, renderer)

        assert engine.is_running is False

    def test_start_sets_running(self, log, renderer):
        engine, _ = build_engine(log, renderer)

        engine.start()

        assert engine.is_running is True

    def test_stop_clears_running(self, log, renderer):
        engine, _ = build_engine(log, renderer)
        engine.start()

        engine.stop()

        assert engine.is_running is False


class TestUpdate:

    def test_feeds_the_clock_delta_into_the_scene(self, log, renderer):
        engine, time = build_engine(log, renderer)
        engine.start()

        time.advance(0.05)
        engine.update()

        assert log == [("update", "Level1", 0.05)]

    def test_does_nothing_while_stopped(self, log, renderer):
        engine, time = build_engine(log, renderer)

        time.advance(0.05)
        engine.update()

        assert log == []

    def test_stopped_engine_does_not_tick_the_clock(self, log, renderer):
        engine, time = build_engine(log, renderer)

        time.advance(2.0)
        engine.update()

        assert engine._clock.elapsed_time == 0.0

    def test_time_spent_paused_does_not_leak_into_the_first_frame(
        self, log, renderer
    ):
        # start() re-ancora o Clock, entao retomar depois de 2s parado
        # da um frame normal em vez de um salto de 0.1s (o teto do
        # clamp, que era tudo que segurava isto antes).
        engine, time = build_engine(log, renderer)

        time.advance(2.0)
        engine.update()

        engine.start()
        engine.update()

        assert log == [("update", "Level1", 0.0)]

    def test_time_spent_before_the_first_start_does_not_leak_either(
        self, log, renderer
    ):
        # Mesmo mecanismo, no caso real: entre construir o Clock e
        # chamar start() cabe o pyxel.init() abrindo a janela.
        engine, time = build_engine(log, renderer)

        time.advance(3.0)
        engine.start()

        time.advance(0.05)
        engine.update()

        # approx: 3.05 - 3.0 nao fecha exato em float.
        assert len(log) == 1
        assert log[0][:2] == ("update", "Level1")
        assert log[0][2] == pytest.approx(0.05)


class TestRender:

    def test_clears_before_drawing_the_scene(self, log, renderer):
        # A ordem importa: limpar depois apagaria o frame inteiro.
        engine, _ = build_engine(log, renderer)
        engine.start()

        engine.render()

        # reset_camera vem da Scene, que reancora o enquadramento em
        # coordenadas de tela quando nenhuma camera esta em uso.
        assert renderer.calls == [("clear", 0), ("reset_camera",)]
        assert log == [("render", "Level1")]

    def test_uses_the_configured_clear_color(self, log, renderer):
        engine, _ = build_engine(log, renderer, clear_color=7)
        engine.start()

        engine.render()

        assert renderer.calls == [("clear", 7), ("reset_camera",)]

    def test_does_nothing_while_stopped(self, log, renderer):
        engine, _ = build_engine(log, renderer)

        engine.render()

        assert renderer.calls == []
        assert log == []


class TestWithoutScene:

    def test_runs_headless_against_an_empty_scene_manager(self, renderer):
        # Regressao do bug do main.py: sem cena registrada o loop tem
        # de seguir girando e apenas limpar a tela, nao explodir.
        engine = Engine(
            clock=Clock(SpyTimeProvider()),
            scene_manager=SceneManager(),
            renderer=renderer,
            input=SpyInput(),
        )
        engine.start()

        engine.update()
        engine.render()

        assert renderer.calls == [("clear", 0)]
