from abc import ABC, abstractmethod


class TileSource(ABC):
    """Que tile ha em cada celula de um tilemap -- para LER, nao desenhar.

    E a segunda porta apoiada no mesmo `.pyxres`, e a separacao e de
    proposito. Colidir exige perguntar "que tile tem aqui?", e isso nao
    e desenhar: enfiar a leitura no `Renderer` obrigaria todo teste de
    colisao a dublar um renderizador inteiro para perguntar sobre
    geometria. Um duble desta porta e um dicionario de cinco linhas, e
    e ele que deixa a suite inteira de colisao rodar sem abrir janela.

    Fala em TILES, e nao em pixels -- ao contrario do `draw_tilemap`.
    Nao e inconsistencia: o desenho recorta uma regiao, e regiao e
    pixel; a leitura pergunta por uma celula, e celula e indice. Cada
    porta usa a unidade da pergunta que responde, e `tile_size` e a
    ponte entre as duas.

    O que a porta devolve e a coordenada do tile no banco de IMAGEM,
    em unidades de tile: `(1, 0)` e "o segundo tile da primeira linha
    do banco". E o modelo do Pyxel, e e o vocabulario que a engine
    possui. O que esse tile SIGNIFICA -- parede, chao, porta -- e
    decisao do jogo, e a engine nao adivinha: quem colide recebe do
    jogo o conjunto de coordenadas que valem como solido.
    """

    @property
    @abstractmethod
    def tile_size(self) -> int:
        """Lado de um tile, em pixels.

        Na porta, e nao fixo em 8: o numero e do backend, e uma engine
        que o escrevesse na mao estaria dizendo um detalhe do Pyxel em
        voz alta. E o fator que converte uma posicao de mundo em indice
        de celula -- e, na outra direcao, uma regiao em tiles numa
        regiao em pixels para o `draw_tilemap`.
        """

    @property
    @abstractmethod
    def width(self) -> int:
        """Largura do mapa, em tiles."""

    @property
    @abstractmethod
    def height(self) -> int:
        """Altura do mapa, em tiles."""

    @abstractmethod
    def get_tile(self, column: int, row: int) -> tuple[int, int]:
        """A coordenada, no banco de imagem, do tile que ocupa a celula.

        `column` e `row` sao INTEIROS, e nao um Vector2D: uma celula e
        um indice discreto, e receber floats aqui obrigaria todo
        chamador a truncar -- e esconderia, dentro de cada um, a
        decisao de para que lado truncar. Quem tem uma posicao de
        mundo divide por `tile_size` e arredonda para baixo ANTES de
        perguntar, e essa conta mora em um lugar so.

        Vale apenas dentro de `[0, width) x [0, height)`. Fora disso o
        adaptador LEVANTA, em vez de repassar o que o backend responde:
        o Pyxel devolve `(0, 0)` para qualquer celula fora do mapa, em
        silencio, e se `(0, 0)` for "vazio" para o jogo o jogador
        atravessa a borda do mundo sem erro nenhum. O que existe fora
        do mapa e decisao de quem colide, e ela precisa ser tomada
        olhando para `width` e `height` -- nao herdada de um valor que
        o backend inventou.
        """
