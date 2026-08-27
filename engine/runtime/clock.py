from engine.ports.time_provider import TimeProvider


class Clock:

    def __init__(
        self,
        time_provider: TimeProvider,
        max_delta_time: float = 0.1,
    ) -> None:
        self._time_provider = time_provider
        self._max_delta_time = max_delta_time

        self._last_time = time_provider.now()

        self.delta_time = 0.0
        self.elapsed_time = 0.0

    def reset(self) -> None:
        # Re-ancora o relogio no instante atual, para que o tempo
        # decorrido fora do loop -- a inicializacao do backend, uma
        # pausa, um breakpoint -- nao vire o dt do proximo frame.
        #
        # NAO zera elapsed_time de proposito: retomar de uma pausa nao
        # pode reiniciar o tempo de jogo acumulado.
        self._last_time = self._time_provider.now()
        self.delta_time = 0.0

    def tick(self) -> float:
        current_time = self._time_provider.now()

        delta_time = current_time - self._last_time

        self._last_time = current_time

        delta_time = min(delta_time, self._max_delta_time)

        self.delta_time = delta_time
        self.elapsed_time += delta_time

        return delta_time
