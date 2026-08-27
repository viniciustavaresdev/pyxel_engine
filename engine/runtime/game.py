from engine.ports.application import Application
from engine.runtime.application_config import ApplicationConfig
from engine.runtime.engine import Engine
from engine.scene.scene import Scene


class Game:

    def __init__(
        self,
        application: Application,
        engine: Engine,
        config: ApplicationConfig,
        initial_scene: Scene | None = None,
    ) -> None:
        self._application = application
        self._engine = engine
        self._config = config
        self._initial_scene = initial_scene

    def run(self) -> None:
        self._application.initialize(self._config)

        # DEPOIS do initialize, nunca antes: change_scene dispara o
        # on_enter da arvore inteira, e uma cena que carregue arte ali
        # precisa da janela e dos bancos de imagem ja existindo.
        if self._initial_scene is not None:
            self._engine.load_scene(self._initial_scene)

        self._engine.start()

        self._application.run(
            self._update,
            self._render,
        )

    def _update(self) -> None:
        self._engine.update()

        # A Engine nao conhece a Application, e nao deve: quem compoe
        # as duas e o Game. Entao e aqui que "a Engine parou" vira
        # "feche a janela" -- no mesmo frame, sem callback nem
        # referencia cruzada.
        if not self._engine.is_running:
            self._application.quit()

    def _render(self) -> None:
        self._engine.render()
