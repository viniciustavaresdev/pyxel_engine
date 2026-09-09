from engine.runtime.engine import Engine
from engine.scene.scene_manager import SceneManager
from tests.conftest import SpyInput, SpyScene


def build_engine(log, renderer, clear_color=0, input=None):
    """Engine real ligada a um SceneManager real e a dubles nas bordas.

    So o desenho e o teclado sao dublados: o objetivo e testar a fiacao
    entre Engine e SceneManager, nao substitui-la por mocks. Nao ha
    relogio a dublar -- a Engine nao mede tempo.
    """
    manager = SceneManager()
    manager.change_scene(SpyScene("Level1", log))
    log.clear()

    engine = Engine(
        scene_manager=manager,
        renderer=renderer,
        input=input if input is not None else SpyInput(),
        clear_color=clear_color,
    )

    return engine


class TestRunningState:
    def test_starts_stopped(self, log, renderer):
        engine = build_engine(log, renderer)

        assert engine.is_running is False

    def test_start_sets_running(self, log, renderer):
        engine = build_engine(log, renderer)

        engine.start()

        assert engine.is_running is True

    def test_stop_clears_running(self, log, renderer):
        engine = build_engine(log, renderer)
        engine.start()

        engine.stop()

        assert engine.is_running is False


class TestUpdate:
    def test_drives_the_scene(self, log, renderer):
        engine = build_engine(log, renderer)
        engine.start()

        engine.update()

        assert log == [("update", "Level1")]

    def test_one_call_is_exactly_one_update(self, log, renderer):
        # O contrato do passo fixo: a Engine nao acumula tempo, nao
        # repete update para "alcancar" o relogio e nao pula nenhum.
        # Cinco chamadas do backend sao cinco frames de jogo, sempre.
        engine = build_engine(log, renderer)
        engine.start()

        for _ in range(5):
            engine.update()

        assert log == [("update", "Level1")] * 5

    def test_does_nothing_while_stopped(self, log, renderer):
        engine = build_engine(log, renderer)

        engine.update()

        assert log == []

    def test_a_long_pause_does_not_change_the_next_frame(self, log, renderer):
        # O que este teste substituiu: tres testes que defendiam o
        # Clock de saltos de tempo -- um breakpoint, uma pausa, o
        # pyxel.init() entre construir e comecar. Sem medicao, nao ha
        # salto a conter: o frame depois da pausa e igual a qualquer
        # outro, e nao por um teto de dt segurando o valor.
        engine = build_engine(log, renderer)

        engine.update()
        engine.start()
        engine.update()

        assert log == [("update", "Level1")]


class TestRender:
    def test_clears_before_drawing_the_scene(self, log, renderer):
        # A ordem importa: limpar depois apagaria o frame inteiro.
        engine = build_engine(log, renderer)
        engine.start()

        engine.render()

        # reset_camera vem da Scene, que reancora o enquadramento em
        # coordenadas de tela quando nenhuma camera esta em uso.
        assert renderer.calls == [("clear", 0), ("reset_camera",)]
        assert log == [("render", "Level1")]

    def test_uses_the_configured_clear_color(self, log, renderer):
        engine = build_engine(log, renderer, clear_color=7)
        engine.start()

        engine.render()

        assert renderer.calls == [("clear", 7), ("reset_camera",)]

    def test_does_nothing_while_stopped(self, log, renderer):
        engine = build_engine(log, renderer)

        engine.render()

        assert renderer.calls == []
        assert log == []


class TestWithoutScene:
    def test_runs_headless_against_an_empty_scene_manager(self, renderer):
        # Regressao do bug do main.py: sem cena registrada o loop tem
        # de seguir girando e apenas limpar a tela, nao explodir.
        engine = Engine(
            scene_manager=SceneManager(),
            renderer=renderer,
            input=SpyInput(),
        )
        engine.start()

        engine.update()
        engine.render()

        assert renderer.calls == [("clear", 0)]
