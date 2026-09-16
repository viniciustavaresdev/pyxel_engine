"""Contrato da porta TileSource, exercido pelo SpyTileSource.

O que se verifica aqui e a fronteira: que a porta fala em TILES (indice
inteiro de celula, coordenada de tile no banco de imagem), que ela e
SEPARADA do Renderer, e que fora do mapa a resposta e uma excecao e
nao um tile inventado. A leitura de um `.pyxres` de verdade e do
adaptador, e esta em tests/adapters/.
"""

import pytest

from engine.ports.renderer import Renderer
from engine.ports.tile_source import TileSource
from tests.conftest import SpyRenderer, SpyTileSource

WALL = (1, 0)
FLOOR = (1, 1)
LEGEND = {"#": WALL, ".": FLOOR}


class TestWhatACellAnswers:
    def test_a_cell_answers_with_a_tile_coordinate(self):
        tiles = SpyTileSource.from_rows(["#.", ".#"], LEGEND)

        assert tiles.get_tile(0, 0) == WALL
        assert tiles.get_tile(1, 0) == FLOOR
        assert tiles.get_tile(0, 1) == FLOOR
        assert tiles.get_tile(1, 1) == WALL

    def test_column_comes_before_row(self):
        # (coluna, linha), como (x, y): a ordem que o `pget` do backend
        # usa e a que uma posicao de mundo dividida por tile_size da.
        tiles = SpyTileSource.from_rows(["#..", "..."], LEGEND)

        assert tiles.get_tile(0, 0) == WALL
        assert tiles.get_tile(0, 1) == FLOOR

    def test_the_answer_is_a_pair_of_ints(self):
        tiles = SpyTileSource.from_rows(["#"], LEGEND)

        u, v = tiles.get_tile(0, 0)

        assert isinstance(u, int) and isinstance(v, int)

    def test_an_unpainted_cell_is_the_zero_tile(self):
        # O que o Pyxel devolve para uma celula nunca pintada. O duble
        # nao inventa outro valor.
        tiles = SpyTileSource({}, width=2, height=2)

        assert tiles.get_tile(1, 1) == (0, 0)


class TestTheMapHasEdges:
    def test_width_and_height_are_in_tiles(self):
        tiles = SpyTileSource.from_rows(["...", "...", "...", "..."], LEGEND)

        assert (tiles.width, tiles.height) == (3, 4)

    def test_tile_size_is_in_pixels_and_comes_from_the_backend(self):
        # 8 e o default do duble porque e o do Pyxel, mas o valor e da
        # porta, e nao da engine: um backend de tiles de 16 responde 16.
        assert SpyTileSource({}, 1, 1).tile_size == 8
        assert SpyTileSource({}, 1, 1, tile_size=16).tile_size == 16

    @pytest.mark.parametrize(
        "column, row",
        [(-1, 0), (0, -1), (3, 0), (0, 2), (3, 2), (99, 99)],
    )
    def test_outside_the_map_raises(self, column, row):
        # E nao devolve (0, 0), que e o que o backend faz em silencio.
        # Se (0, 0) for "chao" para o jogo, "fora do mapa" e "chao"
        # seriam a mesma resposta, e o jogador sairia do mundo sem
        # erro. O que existe fora do mapa e decisao de quem colide.
        tiles = SpyTileSource.from_rows(["...", "..."], LEGEND)

        with pytest.raises(IndexError):
            tiles.get_tile(column, row)

    def test_the_last_cell_is_inside(self):
        tiles = SpyTileSource.from_rows(["..#", "..."], LEGEND)

        assert tiles.get_tile(2, 0) == WALL


class TestFromRows:
    def test_rows_must_share_a_width(self):
        # Um mapa irregular nao e um tilemap, e uma linha curta por
        # descuido viraria celulas (0, 0) que o teste nao desenhou.
        with pytest.raises(ValueError):
            SpyTileSource.from_rows(["...", ".."], LEGEND)

    def test_an_unknown_symbol_fails_loudly(self):
        with pytest.raises(KeyError):
            SpyTileSource.from_rows(["..x"], LEGEND)

    def test_no_rows_is_an_empty_map(self):
        tiles = SpyTileSource.from_rows([], LEGEND)

        assert (tiles.width, tiles.height) == (0, 0)


class TestTheDivisionBetweenReadingAndDrawing:
    """Duas portas sobre o mesmo .pyxres, e e de proposito."""

    def test_a_tile_source_is_not_a_renderer(self):
        # Se um dia `get_tile` migrar para dentro do Renderer, este
        # teste cai e a decisao volta a mesa em vez de mudar em
        # silencio -- e todo teste de colisao passaria a dublar um
        # renderizador para perguntar sobre geometria.
        assert not isinstance(SpyTileSource({}, 1, 1), Renderer)

    def test_a_renderer_is_not_a_tile_source(self):
        assert not isinstance(SpyRenderer(), TileSource)


class TestPortContract:
    def test_spy_tile_source_satisfies_the_port(self):
        assert isinstance(SpyTileSource({}, 1, 1), TileSource)

    def test_the_port_has_no_unimplemented_methods(self):
        assert (
            TileSource.__abstractmethods__ - set(dir(SpyTileSource({}, 1, 1)))
            == set()
        )
