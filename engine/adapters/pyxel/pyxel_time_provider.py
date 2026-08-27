import pyxel

from engine.ports.time_provider import TimeProvider


class PyxelTimeProvider(TimeProvider):
    # Time derived from Pyxel's frame counter instead of a wall clock.
    # `pyxel.run` drives update at a fixed rate, so this yields an
    # exact, jitter-free dt -- at the cost of drifting from real time
    # when the host cannot keep up with the target fps.
    #
    # `pyxel.frame_count` only exists after `pyxel.init`, so a Clock
    # built on this provider must be created after the Application is
    # initialized.

    def __init__(self, fps: int = 30) -> None:
        if fps <= 0:
            raise ValueError("fps must be a positive number of frames.")

        self._fps = fps

    def now(self) -> float:
        return pyxel.frame_count / self._fps
