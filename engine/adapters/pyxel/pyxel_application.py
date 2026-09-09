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

        # Depois do init: os bancos de imagem so existem com a janela
        # ja criada.
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
