import pytest

from engine.runtime.clock import Clock
from tests.conftest import SpyTimeProvider


class TestInitialState:

    def test_starts_with_zero_delta(self):
        assert Clock(SpyTimeProvider()).delta_time == 0.0

    def test_starts_with_zero_elapsed(self):
        assert Clock(SpyTimeProvider()).elapsed_time == 0.0

    def test_first_tick_measures_from_construction_not_from_zero(self):
        # O Clock ancora em now() no __init__. Se ancorasse em 0.0, um
        # provider que ja comeca adiantado devolveria um primeiro dt
        # gigante.
        time = SpyTimeProvider(start=1000.0)
        clock = Clock(time)

        time.advance(0.05)

        # approx e nao ==: a subtracao 1000.05 - 1000.0 nao fecha
        # exato em float, e e assim que perf_counter chega na pratica.
        assert clock.tick() == pytest.approx(0.05)


class TestTick:
    # Os avancos ficam abaixo de 0.1 de proposito: 0.1 e o teto default
    # do clamp, e um valor acima disso mediria o clamp em vez do tick.

    def test_returns_the_elapsed_delta(self):
        time = SpyTimeProvider()
        clock = Clock(time)

        time.advance(0.05)

        assert clock.tick() == 0.05

    def test_publishes_the_delta_as_an_attribute(self):
        time = SpyTimeProvider()
        clock = Clock(time)
        time.advance(0.05)

        clock.tick()

        assert clock.delta_time == 0.05

    def test_consecutive_ticks_do_not_overlap(self):
        # Cada tick mede so o intervalo desde o tick anterior. Se o
        # _last_time nao avancasse, o dt cresceria a cada frame.
        time = SpyTimeProvider()
        clock = Clock(time)

        time.advance(0.05)
        first = clock.tick()

        time.advance(0.05)
        second = clock.tick()

        assert (first, second) == (0.05, 0.05)

    def test_tick_without_time_passing_is_zero(self):
        assert Clock(SpyTimeProvider()).tick() == 0.0

    def test_elapsed_time_accumulates(self):
        time = SpyTimeProvider()
        clock = Clock(time)

        for _ in range(4):
            time.advance(0.05)
            clock.tick()

        assert clock.elapsed_time == pytest.approx(0.2)


class TestReset:

    def test_swallows_the_time_since_the_last_anchor(self):
        time = SpyTimeProvider()
        clock = Clock(time)

        time.advance(2.0)
        clock.reset()

        assert clock.tick() == 0.0

    def test_the_frame_after_reset_measures_normally(self):
        time = SpyTimeProvider()
        clock = Clock(time)

        time.advance(2.0)
        clock.reset()

        time.advance(0.05)

        assert clock.tick() == pytest.approx(0.05)

    def test_clears_the_published_delta(self):
        time = SpyTimeProvider()
        clock = Clock(time)
        time.advance(0.05)
        clock.tick()

        clock.reset()

        assert clock.delta_time == 0.0

    def test_keeps_the_accumulated_game_time(self):
        # Retomar de uma pausa nao pode reiniciar o cronometro do jogo:
        # reset() re-ancora o relogio, nao apaga o passado.
        time = SpyTimeProvider()
        clock = Clock(time)
        time.advance(0.05)
        clock.tick()

        clock.reset()

        assert clock.elapsed_time == pytest.approx(0.05)


class TestMaxDeltaTime:

    def test_clamps_a_long_frame(self):
        # Protege contra o "spiral of death": um freeze de 5s viraria
        # um dt de 5s, teleportando todo mundo atraves das paredes.
        time = SpyTimeProvider()
        clock = Clock(time, max_delta_time=0.1)

        time.advance(5.0)

        assert clock.tick() == 0.1

    def test_clamped_frames_also_clamp_elapsed_time(self):
        # Consequencia deliberada: elapsed_time e tempo de JOGO, nao
        # tempo de parede. Depois de um freeze os dois divergem.
        time = SpyTimeProvider()
        clock = Clock(time, max_delta_time=0.1)

        time.advance(5.0)
        clock.tick()

        assert clock.elapsed_time == 0.1

    def test_does_not_touch_a_normal_frame(self):
        time = SpyTimeProvider()
        clock = Clock(time, max_delta_time=0.1)

        time.advance(1.0 / 60.0)

        assert clock.tick() == pytest.approx(1.0 / 60.0)

    def test_the_default_ceiling_is_a_tenth_of_a_second(self):
        time = SpyTimeProvider()
        clock = Clock(time)

        time.advance(99.0)

        assert clock.tick() == 0.1
