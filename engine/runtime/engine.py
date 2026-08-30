from __future__ import annotations

from engine.ports.input import Input
from engine.ports.renderer import Renderer
from engine.scene.scene import Scene
from engine.scene.scene_manager import SceneManager


class Engine:
    """O laco de frame, do lado de ca da porta.

    Nao mede tempo. Um `update()` e um frame, e a cadencia e de quem
    implementa `Application.run` -- no Pyxel, do proprio `pyxel.run`.
    Um relogio aqui dentro mediria o intervalo entre duas chamadas que
    o backend ja se comprometeu a espacar, e o resultado dessa medicao
    (jitter, um salto depois de um breakpoint) so criava trabalho de
    defesa.
    """

    def __init__(
        self,
        scene_manager: SceneManager,
        renderer: Renderer,
        input: Input,
        clear_color: int = 0,
    ) -> None:
        self._scene_manager = scene_manager
        self._renderer = renderer
        self._input = input
        self._clear_color = clear_color

        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running

    def load_scene(self, scene: Scene) -> None:
        # Existe para que o Game possa trocar de cena DEPOIS de o
        # backend estar de pe. Uma cena que carregue arte no on_enter
        # precisa da janela ja aberta.
        self._scene_manager.change_scene(scene)

    def start(self) -> None:
        self._running = True

    def stop(self) -> None:
        self._running = False

    def update(self) -> None:
        if not self._running:
            return

        self._scene_manager.update(self._input)

    def render(self) -> None:
        if not self._running:
            return

        self._renderer.clear(self._clear_color)

        self._scene_manager.render(self._renderer)
