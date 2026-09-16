"""Testes dos adaptadores Pyxel.

Importam `pyxel`, mas nunca chamam `pyxel.init()`: nada aqui abre
janela. O que se verifica e o contrato -- se o adaptador cobre a porta
inteira e se a tabela de teclas esta completa -- e nao o desenho, que
so o Pyxel poderia responder.
"""

import math
from typing import Any

import pyxel

from engine.adapters.pyxel.pyxel_application import PyxelApplication
from engine.adapters.pyxel.pyxel_input import _PYXEL_KEYS, PyxelInput
from engine.adapters.pyxel.pyxel_pointer import PyxelPointer
from engine.adapters.pyxel.pyxel_renderer import PyxelRenderer
from engine.adapters.pyxel.pyxel_tile_source import PyxelTileSource
from engine.input.key import Key
from engine.math.rect import Rect
from engine.math.vector2d import Vector2D
from engine.ports.application import Application
from engine.ports.input import Input
from engine.ports.pointer import Pointer
from engine.ports.renderer import Renderer
from engine.ports.tile_source import TileSource
from engine.runtime.application_config import ApplicationConfig


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

    def test_the_mouse_buttons_are_mapped_like_any_other_key(self):
        # O ganho de os botoes terem entrado no `Key` em vez de num
        # enum proprio: o teste de completude acima passou a cobri-los
        # de graca, e este so nomeia o caso para que a intencao fique
        # legivel quando alguem acrescentar MOUSE_MIDDLE.
        assert _PYXEL_KEYS[Key.MOUSE_LEFT] == pyxel.MOUSE_BUTTON_LEFT
        assert _PYXEL_KEYS[Key.MOUSE_RIGHT] == pyxel.MOUSE_BUTTON_RIGHT

    def test_a_mouse_button_is_not_a_keyboard_constant(self):
        # Os dois vivem no mesmo mapa, mas nao no mesmo espaco de
        # valores do Pyxel. Se um dia colidirem, `btn` responderia pela
        # tecla errada -- e o teste de constantes distintas acima ja
        # falharia; este diz por que aquele importa.
        keyboard = {
            value
            for key, value in _PYXEL_KEYS.items()
            if key not in (Key.MOUSE_LEFT, Key.MOUSE_RIGHT)
        }

        assert _PYXEL_KEYS[Key.MOUSE_LEFT] not in keyboard
        assert _PYXEL_KEYS[Key.MOUSE_RIGHT] not in keyboard


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

    def test_pyxel_pointer(self):
        assert isinstance(PyxelPointer(), Pointer)

    def test_pyxel_tile_source(self):
        assert isinstance(PyxelTileSource(0), TileSource)


class TestPyxelApplicationAppliesTheConfig:
    """O que o `initialize` faz alem de abrir a janela.

    Monkeypatch em tudo: `pyxel.init` de verdade abriria janela, e o
    que precisa ser travado aqui e a ORDEM -- nem cursor nem banco de
    imagem existem antes de haver janela.
    """

    def _record(self, monkeypatch):
        # Anotado porque as tres chamadas tem aridades diferentes: sem
        # isto o mypy fixa o tipo da lista na primeira delas.
        calls: list[tuple[Any, ...]] = []

        monkeypatch.setattr(
            pyxel, "init", lambda *a, **k: calls.append(("init", a, k))
        )
        monkeypatch.setattr(
            pyxel, "mouse", lambda visible: calls.append(("mouse", visible))
        )
        monkeypatch.setattr(
            pyxel, "load", lambda path: calls.append(("load", path))
        )

        return calls

    def test_the_cursor_is_hidden_by_default(self, monkeypatch):
        # O default do proprio Pyxel, e o certo para um jogo so de
        # teclado: ninguem deve ganhar um cursor por acidente.
        calls = self._record(monkeypatch)

        PyxelApplication().initialize(
            ApplicationConfig(width=160, height=120, title="T")
        )

        assert ("mouse", False) in calls

    def test_show_cursor_reaches_the_backend(self, monkeypatch):
        calls = self._record(monkeypatch)

        PyxelApplication().initialize(
            ApplicationConfig(
                width=160, height=120, title="T", show_cursor=True
            )
        )

        assert ("mouse", True) in calls

    def test_the_cursor_is_set_after_the_window_exists(self, monkeypatch):
        # Antes do init nao ha janela, e portanto nao ha estado de
        # cursor para ligar. Mesma regra do `load`.
        calls = self._record(monkeypatch)

        PyxelApplication().initialize(
            ApplicationConfig(
                width=160,
                height=120,
                title="T",
                show_cursor=True,
                resource_path="game.pyxres",
            )
        )

        names = [call[0] for call in calls]

        assert names == ["init", "mouse", "load"]

    def test_no_resource_means_no_load(self, monkeypatch):
        calls = self._record(monkeypatch)

        PyxelApplication().initialize(
            ApplicationConfig(width=160, height=120, title="T")
        )

        assert [call[0] for call in calls] == ["init", "mouse"]


class TestPyxelPointerReadsTheCursor:
    """A leitura do cursor, sem abrir janela.

    Monkeypatch nos atributos de modulo do Pyxel: sem `pyxel.init()`
    eles existem zerados, e o que precisa ser travado aqui e a
    CONVERSAO -- inteiros do backend viram float da engine, em um
    Vector2D e em coordenadas de tela.
    """

    def test_it_reports_the_cursor_as_a_vector(self, monkeypatch):
        monkeypatch.setattr(pyxel, "mouse_x", 120)
        monkeypatch.setattr(pyxel, "mouse_y", 45)

        assert PyxelPointer().get_position() == Vector2D(120.0, 45.0)

    def test_the_integers_become_floats(self, monkeypatch):
        # O Pyxel conta o cursor em pixel inteiro. Promover na fronteira
        # evita que a primeira conta do jogo -- subtrair a posicao do
        # jogador para achar a direcao da mira -- promova sozinha, num
        # lugar onde ninguem esta olhando.
        monkeypatch.setattr(pyxel, "mouse_x", 7)
        monkeypatch.setattr(pyxel, "mouse_y", 9)

        position = PyxelPointer().get_position()

        assert isinstance(position.x, float)
        assert isinstance(position.y, float)

    def test_it_reads_the_current_frame_every_time(self, monkeypatch):
        # Sem estado proprio: o adaptador nao guarda copia, entao nao
        # ha o que dessincronizar do backend.
        pointer = PyxelPointer()

        monkeypatch.setattr(pyxel, "mouse_x", 1)
        monkeypatch.setattr(pyxel, "mouse_y", 2)
        first = pointer.get_position()

        monkeypatch.setattr(pyxel, "mouse_x", 30)
        monkeypatch.setattr(pyxel, "mouse_y", 40)
        second = pointer.get_position()

        assert (first, second) == (Vector2D(1.0, 2.0), Vector2D(30.0, 40.0))

    def test_a_cursor_outside_the_window_is_not_clamped(self, monkeypatch):
        # O Pyxel devolve negativo quando o cursor sai pela esquerda ou
        # pelo topo. A porta repassa: prender ao viewport aqui seria o
        # adaptador decidindo uma regra de jogo, e um jogo que queira
        # mirar para fora da tela nao teria como desfazer.
        monkeypatch.setattr(pyxel, "mouse_x", -12)
        monkeypatch.setattr(pyxel, "mouse_y", 999)

        assert PyxelPointer().get_position() == Vector2D(-12.0, 999.0)


class _FakeTilemap:
    """O que o adaptador toca de um `pyxel.Tilemap`: width, height, pget.

    Reproduz o comportamento REAL do pget fora do mapa -- devolve
    (0, 0) sem reclamar -- porque e exatamente contra isso que o
    adaptador se defende, e um dublê que levantasse sozinho deixaria o
    teste passar sem a guarda existir.
    """

    def __init__(self, tiles, width, height):
        self.tiles = tiles
        self.width = width
        self.height = height

    def pget(self, x, y):
        return self.tiles.get((x, y), (0, 0))


class TestPyxelTileSourceReadsTheTilemap:
    """A leitura de um banco de tilemap, sem abrir janela.

    Monkeypatch em `pyxel.tilemaps`: sem `pyxel.init()` a lista nem
    existe, e o que precisa ser travado aqui e a TRADUCAO -- coluna e
    linha em tiles chegam ao pget na mesma ordem, o tamanho do tile vem
    do backend, e a guarda de borda transforma o (0, 0) silencioso do
    Pyxel em erro.
    """

    def _install(self, monkeypatch, *tilemaps):
        monkeypatch.setattr(pyxel, "tilemaps", list(tilemaps), raising=False)

    def test_it_reads_the_tile_at_column_and_row(self, monkeypatch):
        self._install(
            monkeypatch, _FakeTilemap({(3, 1): (2, 0)}, width=8, height=8)
        )

        assert PyxelTileSource(0).get_tile(3, 1) == (2, 0)

    def test_the_index_selects_the_bank(self, monkeypatch):
        self._install(
            monkeypatch,
            _FakeTilemap({(0, 0): (1, 0)}, width=4, height=4),
            _FakeTilemap({(0, 0): (5, 5)}, width=4, height=4),
        )

        assert PyxelTileSource(1).get_tile(0, 0) == (5, 5)

    def test_width_and_height_come_from_the_bank(self, monkeypatch):
        self._install(monkeypatch, _FakeTilemap({}, width=39, height=24))

        source = PyxelTileSource(0)

        assert (source.width, source.height) == (39, 24)

    def test_tile_size_comes_from_the_backend_constant(self, monkeypatch):
        # A engine nunca escreve 8. Se o Pyxel um dia mudar a constante,
        # a porta responde o valor novo sem uma linha na engine.
        monkeypatch.setattr(pyxel, "TILE_SIZE", 16)

        assert PyxelTileSource(0).tile_size == 16

    def test_outside_the_map_raises_instead_of_answering_zero(
        self, monkeypatch
    ):
        # O backend responderia (0, 0) aqui, e (0, 0) e um tile
        # legitimo. O adaptador cumpre o que a porta promete.
        self._install(monkeypatch, _FakeTilemap({}, width=4, height=4))

        source = PyxelTileSource(0)

        for column, row in [(-1, 0), (0, -1), (4, 0), (0, 4)]:
            try:
                source.get_tile(column, row)
            except IndexError:
                continue

            raise AssertionError(f"({column}, {row}) did not raise")

    def test_it_resolves_the_bank_on_every_call(self, monkeypatch):
        # Guarda o INDICE, nao o objeto: `pyxel.load` troca os bancos
        # inteiros, e um adaptador construido antes do initialize -- o
        # caso normal -- apontaria para um tilemap que deixou de
        # existir.
        source = PyxelTileSource(0)

        self._install(monkeypatch, _FakeTilemap({}, width=1, height=1))
        before = source.get_tile(0, 0)

        self._install(
            monkeypatch, _FakeTilemap({(0, 0): (7, 7)}, width=1, height=1)
        )
        after = source.get_tile(0, 0)

        assert (before, after) == ((0, 0), (7, 7))


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


class TestPyxelRendererTilemap:
    """A traducao do draw_tilemap para o bltm.

    Monkeypatch pelo mesmo motivo do draw_sprite: bltm sem janela nao
    roda, e o que precisa ser travado e a passagem dos argumentos --
    em especial que a regiao chega em PIXELS, sem multiplicacao por
    tamanho de tile. Foi verificado desenhando em uma janela minima
    que e essa a unidade do bltm; se o Pyxel mudar isso um dia, e este
    teste que precisa mudar junto, e nao o codigo de jogo.
    """

    def _record(self, monkeypatch):
        calls = []
        monkeypatch.setattr(pyxel, "bltm", lambda *args: calls.append(args))

        return calls

    def test_the_corner_and_region_pass_straight_through(self, monkeypatch):
        calls = self._record(monkeypatch)

        PyxelRenderer().draw_tilemap(
            Vector2D(10.0, 20.0), 0, Rect(16.0, 8.0, 160.0, 120.0)
        )

        assert calls[0] == (10.0, 20.0, 0, 16.0, 8.0, 160.0, 120.0, None)

    def test_the_tilemap_index_selects_the_bank(self, monkeypatch):
        calls = self._record(monkeypatch)

        PyxelRenderer().draw_tilemap(Vector2D(), 3, Rect(0.0, 0.0, 8.0, 8.0))

        assert calls[0][2] == 3

    def test_the_color_key_reaches_the_backend(self, monkeypatch):
        calls = self._record(monkeypatch)

        PyxelRenderer().draw_tilemap(
            Vector2D(), 0, Rect(0.0, 0.0, 8.0, 8.0), color_key=0
        )

        assert calls[0][-1] == 0

    def test_a_fractional_corner_is_not_rounded(self, monkeypatch):
        # Mesma politica dos outros metodos: o adaptador nao prende a
        # grade. Um tilemap desenhado sob uma camera fracionaria segue
        # a camera, e nao salta de pixel em pixel sozinho.
        calls = self._record(monkeypatch)

        PyxelRenderer().draw_tilemap(
            Vector2D(0.5, -0.25), 0, Rect(0.0, 0.0, 8.0, 8.0)
        )

        assert calls[0][:2] == (0.5, -0.25)


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

    def test_draw_line_passes_both_ends_untouched(self, monkeypatch):
        calls = []
        monkeypatch.setattr(pyxel, "line", lambda *args: calls.append(args))

        PyxelRenderer().draw_line(Vector2D(1.5, 2.5), Vector2D(30.25, 40.0), 8)

        assert calls[0] == (1.5, 2.5, 30.25, 40.0, 8)

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
