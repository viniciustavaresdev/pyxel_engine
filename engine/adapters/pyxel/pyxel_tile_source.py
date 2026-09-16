import pyxel

from engine.ports.tile_source import TileSource


class PyxelTileSource(TileSource):
    """Le um banco de tilemap do `.pyxres` carregado pelo `pyxel.load`.

    Guarda so o INDICE do banco, e nao o objeto `Tilemap`: `pyxel.load`
    substitui os bancos inteiros, e um adaptador construido antes do
    `initialize` -- o caso normal, ja que o jogo monta a cena antes de
    rodar -- ficaria apontando para um tilemap vazio que deixou de
    existir. Resolver `pyxel.tilemaps[i]` a cada pergunta custa uma
    indexacao e garante que a resposta e sempre a do banco atual.
    """

    def __init__(self, tilemap: int) -> None:
        self._tilemap = tilemap

    @property
    def tile_size(self) -> int:
        # Lido do backend, nunca escrito aqui: e o unico lugar da engine
        # que sabe que um tile do Pyxel tem 8 pixels, e ele nao sabe --
        # ele pergunta.
        return int(pyxel.TILE_SIZE)

    @property
    def width(self) -> int:
        return int(pyxel.tilemaps[self._tilemap].width)

    @property
    def height(self) -> int:
        return int(pyxel.tilemaps[self._tilemap].height)

    def get_tile(self, column: int, row: int) -> tuple[int, int]:
        tilemap = pyxel.tilemaps[self._tilemap]

        # O pget do Pyxel devolve (0, 0) para qualquer celula fora do
        # mapa, em silencio -- e (0, 0) e um tile legitimo, geralmente
        # o vazio. Deixar passar faria "fora do mapa" e "chao" serem a
        # mesma resposta, e o jogador sairia do mundo sem erro. A porta
        # promete levantar, e e aqui que a promessa se cumpre.
        if not (0 <= column < tilemap.width and 0 <= row < tilemap.height):
            raise IndexError(
                f"Tile ({column}, {row}) is outside the "
                f"{tilemap.width}x{tilemap.height} tilemap {self._tilemap}."
            )

        # O pget devolve uma tupla de dois ints ja em unidades de tile
        # do banco de imagem -- o mesmo vocabulario da porta, sem
        # conversao.
        u, v = tilemap.pget(column, row)

        return (int(u), int(v))
