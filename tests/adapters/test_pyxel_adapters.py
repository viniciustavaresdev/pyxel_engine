"""Testes dos adaptadores Pyxel.

Importam `pyxel`, mas nunca chamam `pyxel.init()`: nada aqui abre
janela. O que se verifica e o contrato -- se o adaptador cobre a porta
inteira e se a tabela de teclas esta completa -- e nao o desenho, que
so o Pyxel poderia responder.
"""

import math

import pyxel

from engine.adapters.pyxel.pyxel_application import PyxelApplication
from engine.adapters.pyxel.pyxel_input import _PYXEL_KEYS, PyxelInput
from engine.adapters.pyxel.pyxel_renderer import PyxelRenderer
from engine.adapters.pyxel.pyxel_time_provider import PyxelTimeProvider
from engine.adapters.stdlib.performance_time_provider import (
    PerformanceTimeProvider,
)
from engine.input.key import Key
from engine.math.rect import Rect
from engine.math.vector2d import Vector2D
from engine.ports.application import Application
from engine.ports.input import Input
from engine.ports.renderer import Renderer
from engine.ports.time_provider import TimeProvider


class TestKeyMapCompleteness:

    def test_every_key_has_a_pyxel_constant(self):
        # O teste que paga o preco do enum proprio: acrescentar uma Key
        # e esquecer do mapa daria KeyError no meio do jogo, no frame
        # em que o jogador apertasse a tecla. Aqui falha no build.
        missing = [key.name for key in Key if key not in _PYXEL_KEYS]

        assert missing == []

    def test_the_map_has_no_extra_entries(self):
        assert set(_PYXEL_KEYS) == set(Key)

    def test_no_two_keys_share_a_pyxel_constant(self):
        # Copiar e colar uma linha do mapa sem trocar a constante faria
        # duas teclas diferentes responderem juntas.
        constants = list(_PYXEL_KEYS.values())

        assert len(constants) == len(set(constants))

    def test_constants_are_integers(self):
        assert all(isinstance(value, int) for value in _PYXEL_KEYS.values())


class TestAdaptersSatisfyTheirPorts:
    """Cada adaptador tem de implementar a porta inteira.

    ABCs so cobram os metodos abstratos na hora de instanciar -- e o
    que estes testes fazem. Sem eles, um metodo novo na porta so
    apareceria quando o jogo tentasse usa-lo.
    """

    def test_pyxel_application(self):
        assert isinstance(PyxelApplication(), Application)

    def test_pyxel_renderer(self):
        assert isinstance(PyxelRenderer(), Renderer)

    def test_pyxel_input(self):
        assert isinstance(PyxelInput(), Input)

    def test_pyxel_time_provider(self):
        assert isinstance(PyxelTimeProvider(), TimeProvider)

    def test_performance_time_provider(self):
        assert isinstance(PerformanceTimeProvider(), TimeProvider)


class TestPyxelRendererSpriteOrigin:
    """A traducao centro -> canto exigida pelo blt.

    Monkeypatch em vez de desenho de verdade: chamar pyxel.blt sem
    janela nao roda. O que precisa ser travado aqui e a CONTA, e ela
    aparece inteira nos argumentos.

    A conta so esta certa porque o blt do Pyxel preserva o centro da
    regiao ao girar e ao escalar -- comportamento verificado
    desenhando em uma pyxel.Image fora da tela.
    """

    def _record(self, monkeypatch):
        calls = []
        monkeypatch.setattr(pyxel, "blt", lambda *args: calls.append(args))

        return calls

    def test_backs_off_half_a_region_from_the_center(self, monkeypatch):
        calls = self._record(monkeypatch)

        PyxelRenderer().draw_sprite(
            Vector2D(100.0, 50.0), 0, Rect(8.0, 16.0, 8.0, 8.0)
        )

        assert calls[0][:2] == (96, 46)

    def test_an_odd_region_keeps_the_exact_center(self, monkeypatch):
        # Regiao impar cai em meio pixel, e o adaptador NAO arredonda:
        # o centro chega ao backend exato. Prender a grade e politica de
        # pixel art, e se um dia existir tem de valer para posicao,
        # tamanho e camera juntos -- nao escondida dentro deste metodo.
        calls = self._record(monkeypatch)

        PyxelRenderer().draw_sprite(
            Vector2D(100.0, 50.0), 0, Rect(0.0, 0.0, 5.0, 5.0)
        )

        assert calls[0][:2] == (97.5, 47.5)

    def test_the_scale_does_not_enter_the_correction(self, monkeypatch):
        # O Pyxel calcula o centro que preserva com a regiao SEM escala.
        # Descontar a regiao ja escalada aqui faria um sprite ampliado
        # deslizar para fora do proprio centro.
        calls = self._record(monkeypatch)

        PyxelRenderer().draw_sprite(
            Vector2D(100.0, 50.0),
            0,
            Rect(0.0, 0.0, 8.0, 8.0),
            scale=4.0,
        )

        assert calls[0][:2] == (96, 46)

    def test_radians_reach_pyxel_as_degrees(self, monkeypatch):
        calls = self._record(monkeypatch)

        PyxelRenderer().draw_sprite(
            Vector2D(),
            0,
            Rect(0.0, 0.0, 8.0, 8.0),
            rotation=math.pi / 2.0,
        )

        assert calls[0][8] == 90.0


class TestTheAdapterDoesNotSnapToTheGrid:
    """Prender o desenho a grade e politica, e nao mora aqui.

    A engine passa float e o adaptador repassa float. Arredondar em um
    metodo so daria um retangulo alinhado e um sprite subpixel na mesma
    cena, com a camera fracionaria por baixo dos dois -- que e pior que
    qualquer uma das duas escolhas feita inteira.
    """

    def test_draw_rect_passes_the_position_untouched(self, monkeypatch):
        calls = []
        monkeypatch.setattr(pyxel, "rect", lambda *args: calls.append(args))

        PyxelRenderer().draw_rect(Vector2D(10.5, 20.5), Vector2D(4.5, 8.5), 11)

        assert calls[0] == (10.5, 20.5, 4.5, 8.5, 11)

    def test_draw_text_passes_the_position_untouched(self, monkeypatch):
        calls = []
        monkeypatch.setattr(pyxel, "text", lambda *args: calls.append(args))

        PyxelRenderer().draw_text(Vector2D(4.5, 4.5), "HP", 7)

        assert calls[0] == (4.5, 4.5, "HP", 7)

    def test_the_camera_offset_is_not_rounded_either(self, monkeypatch):
        # O caso que mais aparece: uma camera seguindo o jogador tem
        # offset fracionario quase sempre.
        calls = []
        monkeypatch.setattr(pyxel, "camera", lambda *args: calls.append(args))

        PyxelRenderer().set_camera(Vector2D(-30.5, 40.25))

        assert calls[0] == (-30.5, 40.25)


class TestPyxelTimeProvider:

    def test_rejects_a_non_positive_fps(self):
        for fps in (0, -1):
            try:
                PyxelTimeProvider(fps=fps)
            except ValueError:
                continue

            raise AssertionError(f"fps={fps} deveria ter sido rejeitado")

    def test_converts_frames_into_seconds(self):
        # frame_count e 0 fora do loop, entao o que da para afirmar sem
        # abrir janela e a conversao em si.
        provider = PyxelTimeProvider(fps=60)

        assert provider.now() == 0.0
