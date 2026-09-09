from collections.abc import Callable

import pyxel

from engine.ports.application import Application
from engine.runtime.application_config import ApplicationConfig


class PyxelApplication(Application):
    def initialize(
        self,
        config: ApplicationConfig,
    ) -> None:
        pyxel.init(
            config.width,
            config.height,
            title=config.title,
            fps=config.fps,
        )

        # Os dois DEPOIS do init, e pelo mesmo motivo: nao ha janela
        # antes dele, e nem banco de imagem nem estado de cursor
        # existem sem ela.
        pyxel.mouse(config.show_cursor)

        if config.resource_path is not None:
            pyxel.load(config.resource_path)

    def run(
        self,
        update: Callable[[], None],
        render: Callable[[], None],
    ) -> None:
        pyxel.run(update, render)

    def quit(self) -> None:
        pyxel.quit()
