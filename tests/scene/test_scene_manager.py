from engine.scene.scene import Scene
from engine.scene.scene_manager import SceneManager
from tests.conftest import SpyNode, SpyScene


class TestInitialState:

    def test_starts_without_a_scene(self):
        assert SceneManager().current_scene is None

    def test_starts_inactive(self):
        assert SceneManager().has_active_scene is False


class TestChangeScene:

    def test_becomes_the_current_scene(self):
        manager = SceneManager()
        scene = Scene("Level1")

        manager.change_scene(scene)

        assert manager.current_scene is scene
        assert manager.has_active_scene is True

    def test_enters_the_new_scene(self, log):
        manager = SceneManager()

        manager.change_scene(SpyScene("Level1", log))

        assert log == [("enter", "Level1")]

    def test_enters_the_whole_subtree(self, log):
        # change_scene tem de acordar a arvore inteira, nao so a raiz.
        # Este era o caminho que quebrava com TypeError enquanto
        # on_enter estava declarado sem `self`.
        manager = SceneManager()
        scene = SpyScene("Level1", log)
        scene.add_child(SpyNode("Child", log))

        manager.change_scene(scene)

        assert log == [("enter", "Level1"), ("enter", "Child")]

    def test_exits_the_previous_scene_before_entering_the_next(self, log):
        manager = SceneManager()
        manager.change_scene(SpyScene("Level1", log))
        log.clear()

        manager.change_scene(SpyScene("Level2", log))

        assert log == [("exit", "Level1"), ("enter", "Level2")]

    def test_replacing_the_same_scene_is_a_no_op(self, log):
        # Sem esta guarda, trocar para a cena ja ativa a derrubaria e
        # reconstruiria -- perdendo o estado do jogo em silencio.
        manager = SceneManager()
        scene = SpyScene("Level1", log)
        manager.change_scene(scene)
        log.clear()

        manager.change_scene(scene)

        assert log == []
        assert manager.current_scene is scene


class TestDelegation:

    def test_update_reaches_the_current_scene(self, log, spy_input):
        manager = SceneManager()
        manager.change_scene(SpyScene("Level1", log))
        log.clear()

        manager.update(spy_input)

        assert log == [("update", "Level1")]

    def test_render_reaches_the_current_scene(self, log, renderer):
        manager = SceneManager()
        manager.change_scene(SpyScene("Level1", log))
        log.clear()

        manager.render(renderer)

        assert log == [("render", "Level1")]

    def test_only_the_current_scene_runs(self, log, spy_input):
        # A cena antiga tem de ficar de fato inerte depois da troca.
        manager = SceneManager()
        manager.change_scene(SpyScene("Level1", log))
        manager.change_scene(SpyScene("Level2", log))
        log.clear()

        manager.update(spy_input)

        assert log == [("update", "Level2")]


class TestWithoutScene:

    def test_update_without_a_scene_is_a_no_op(self, spy_input):
        SceneManager().update(spy_input)

    def test_render_without_a_scene_is_a_no_op(self, renderer):
        manager = SceneManager()

        manager.render(renderer)

        assert renderer.calls == []
