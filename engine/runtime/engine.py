from __future__ import annotations

from engine.ports.input import Input
from engine.ports.renderer import Renderer
from engine.runtime.clock import Clock
from engine.scene.scene import Scene
from engine.scene.scene_manager import SceneManager


class Engine:

    def __init__(
        self,
        clock: Clock,
        scene_manager: SceneManager,
        renderer: Renderer,
        input: Input,
        clear_color: int = 0,
    ) -> None:
        self._clock = clock
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
        # Antes de marcar running: o Clock ancorou na propria
        # construcao, e entre aquilo e aqui coube abrir a janela do
        # backend. Sem o reset esse tempo apareceria no primeiro dt.
        self._clock.reset()

        self._running = True

    def stop(self) -> None:
        self._running = False

    def update(self) -> None:
        if not self._running:
            return

        dt = self._clock.tick()

        self._scene_manager.update(dt, self._input)

    def render(self) -> None:
        if not self._running:
            return

        self._renderer.clear(self._clear_color)

        self._scene_manager.render(self._renderer)
