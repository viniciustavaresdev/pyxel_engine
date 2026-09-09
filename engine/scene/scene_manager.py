from __future__ import annotations

from engine.ports.input import Input
from engine.ports.renderer import Renderer
from engine.scene.scene import Scene


class SceneManager:
    def __init__(self) -> None:
        self._current_scene: Scene | None = None

    @property
    def current_scene(self) -> Scene | None:
        return self._current_scene

    @property
    def has_active_scene(self) -> bool:
        return self._current_scene is not None

    def change_scene(self, scene: Scene) -> None:
        if scene is self._current_scene:
            return

        if self._current_scene is not None:
            self._current_scene.exit()

        self._current_scene = scene
        self._current_scene.enter()

    def update(self, input: Input) -> None:
        if self._current_scene is None:
            return

        self._current_scene.update(input)

    def render(self, renderer: Renderer) -> None:
        if self._current_scene is None:
            return

        self._current_scene.render(renderer)
