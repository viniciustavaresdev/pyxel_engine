import math

import pyxel

from engine.math.rect import Rect
from engine.math.vector2d import Vector2D
from engine.ports.renderer import Renderer


class PyxelRenderer(Renderer):
    # Unico lugar que desmonta Vector2D e Rect em escalares. E o
    # trabalho do adaptador: o Pyxel fala em numeros soltos, a engine
    # fala em valores, e a traducao mora aqui em vez de em cada no.

    def clear(self, color: int = 0) -> None:
        pyxel.cls(color)

    def draw_rect(
        self,
        position: Vector2D,
        size: Vector2D,
        color: int,
    ) -> None:
        # Passa float direto, sem arredondar: o Pyxel aceita, e o
        # adaptador nao e o lugar de decidir isso.
        #
        # Prender o desenho a grade de pixels e POLITICA, e politica
        # precisa valer inteira ou nao valer. Arredondar so aqui daria
        # um retangulo alinhado e um sprite subpixel na mesma cena, com
        # a camera fracionaria por baixo dos dois. Se um dia existir,
        # entra como uma funcao unica aplicada a posicao, tamanho e
        # camera junto -- e com round(), nao int(), que trunca em
        # direcao ao zero e desloca meio pixel em coordenada negativa.
        pyxel.rect(
            position.x,
            position.y,
            size.x,
            size.y,
            color,
        )

    def draw_sprite(
        self,
        center: Vector2D,
        image: int,
        region: Rect,
        color_key: int | None = None,
        rotation: float = 0.0,
        scale: float = 1.0,
    ) -> None:
        # O blt do Pyxel recebe o CANTO da regiao nao girada, mas gira e
        # escala em torno do CENTRO dela -- ou seja, mantem o centro
        # fixo em (x + w/2, y + h/2). Verificado desenhando em uma
        # pyxel.Image fora da tela: girar 90 graus ou dobrar a escala
        # muda a caixa desenhada e nao mexe no centro dela.
        #
        # Entao a conversao e so recuar meia regiao. Metade da regiao
        # SEM a escala, de novo porque e assim que o Pyxel calcula o
        # centro que ele mesmo preserva.
        pyxel.blt(
            (center.x - region.width / 2.0),
            (center.y - region.height / 2.0),
            image,
            region.x,
            region.y,
            region.width,
            region.height,
            color_key,
            # A engine fala em radianos; o Pyxel espera graus.
            math.degrees(rotation),
            scale,
        )

    def draw_tilemap(
        self,
        position: Vector2D,
        tilemap: int,
        region: Rect,
        color_key: int | None = None,
    ) -> None:
        # O bltm fala em PIXELS nos quatro valores da regiao (u, v, w,
        # h), e nao em tiles -- verificado desenhando em uma janela
        # minima: `bltm(0, 0, 0, 8, 8, 8, 8)` copia o tile (1, 1) do
        # mapa, nao o (8, 8). Por isso a regiao da porta passa direto,
        # sem multiplicar por TILE_SIZE. Quem conta em tiles e o
        # `Tilemap.pget`, do outro lado, e e a porta `TileSource` que
        # traduz aquele vocabulario.
        pyxel.bltm(
            position.x,
            position.y,
            tilemap,
            region.x,
            region.y,
            region.width,
            region.height,
            color_key,
        )

    def draw_line(
        self,
        start: Vector2D,
        end: Vector2D,
        color: int,
    ) -> None:
        # Float direto, como nos outros: o Pyxel aceita, e prender a
        # grade e politica que nao mora aqui.
        pyxel.line(start.x, start.y, end.x, end.y, color)

    def draw_text(
        self,
        position: Vector2D,
        text: str,
        color: int,
    ) -> None:
        pyxel.text(position.x, position.y, text, color)

    def set_camera(self, offset: Vector2D) -> None:
        pyxel.camera(offset.x, offset.y)

    def reset_camera(self) -> None:
        # pyxel.camera() sem argumentos volta para (0, 0).
        pyxel.camera()
