from __future__ import annotations

from dataclasses import dataclass

from engine.math.vector2d import Vector2D


@dataclass(frozen=True, slots=True)
class Rect:
    """Regiao retangular, em quatro floats.

    Serve a dois papeis de proposito: a regiao de um sprite dentro do
    atlas, que o backend recorta, e a caixa alinhada aos eixos de um no
    no mundo, que `VisualNode.get_world_bounds()` devolve. Sao a mesma
    forma -- canto e tamanho -- e separa-las em duas classes custaria
    uma conversao em toda fronteira sem comprar garantia nenhuma.

    frozen porque e um valor, nao um objeto com ciclo de vida: a
    regiao de um sprite dentro do atlas e definida uma vez e passa a
    ser compartilhada por todo frame que a desenha. Congelada, ela
    pode ser guardada como constante de classe sem risco de alguem
    escrever nela por engano.

    Guarda floats soltos em vez de dois Vector2D. Ja foi por defesa --
    um Vector2D mutavel embutido daria um Rect frozen por fora e
    mutavel por dentro. Com o vetor congelado o motivo passou a ser
    outro, e continua valendo: sao os quatro numeros que o backend
    recebe, e guarda-los planos evita construir dois vetores em toda
    caixa que so vai ser desmontada de novo do outro lado.
    """

    x: float
    y: float
    width: float
    height: float

    @classmethod
    def from_center_size(cls, center: Vector2D, size: Vector2D) -> Rect:
        """Caixa de `size` centrada em `center`.

        A ponte entre o vocabulario de quem calcula e o de quem
        desenha: a engine resolve posicao de no em CENTRO -- e o unico
        ponto que sobrevive a rotacao e a qualquer anchor -- enquanto
        um retangulo se descreve pelo canto. Esta e a unica conversao
        entre os dois, em vez de uma subtracao de meio tamanho repetida
        em cada chamador.
        """
        return cls(
            center.x - size.x / 2.0,
            center.y - size.y / 2.0,
            size.x,
            size.y,
        )

    @property
    def position(self) -> Vector2D:
        return Vector2D(self.x, self.y)

    @property
    def size(self) -> Vector2D:
        return Vector2D(self.width, self.height)

    @property
    def center(self) -> Vector2D:
        return Vector2D(
            self.x + self.width / 2.0,
            self.y + self.height / 2.0,
        )

    def normalized(self) -> Rect:
        """A mesma regiao com largura e altura nao-negativas.

        Largura negativa e o idioma de espelhamento do backend -- e
        assim que se vira um personagem sem uma segunda arte. Para
        recortar um atlas o sinal quer dizer alguma coisa; para
        perguntar se um ponto caiu dentro, nao quer dizer nada, e um
        retangulo de largura -8 responderia "nunca" a toda pergunta,
        em silencio.

        Devolve `self` quando ja esta normalizado, entao o caminho
        comum nao aloca.
        """
        if self.width >= 0.0 and self.height >= 0.0:
            return self

        return Rect(
            self.x + min(self.width, 0.0),
            self.y + min(self.height, 0.0),
            abs(self.width),
            abs(self.height),
        )

    def contains(self, point: Vector2D) -> bool:
        """O ponto caiu dentro da caixa?

        Intervalo SEMIABERTO: a borda de cima e a da esquerda contam,
        as de baixo e da direita nao. E a convencao que faz caixas
        encostadas ladrilharem o plano sem que a linha compartilhada
        pertenca as duas -- num grid de tiles, um ponto sobre a divisa
        cai em exatamente um tile, e nao em dois.

        Consequencia coerente: uma caixa de largura zero nao contem
        ponto nenhum.
        """
        rect = self.normalized()

        return (
            rect.x <= point.x < rect.x + rect.width
            and rect.y <= point.y < rect.y + rect.height
        )

    def intersects(self, other: Rect) -> bool:
        """As duas caixas se sobrepoem?

        AABB classico: sobrepoem quando NAO ha eixo em que uma termine
        antes de a outra comecar. Encostar nao e sobrepor, pela mesma
        regra semiaberta do `contains` -- um jogador parado exatamente
        sobre o chao nao esta afundado nele.

        A definicao exata e "existe ponto que as duas contem", e e dela
        que sai a guarda de area zero: uma caixa vazia nao contem ponto
        nenhum, entao nao sobrepoe nada -- nem quando esta bem no meio
        da outra, que e o que a comparacao de bordas sozinha
        responderia. Um no sem tamanho e um marco de spawn, nao um
        corpo, e nao deve colidir com parede.
        """
        a = self.normalized()
        b = other.normalized()

        if a.width <= 0.0 or a.height <= 0.0:
            return False

        if b.width <= 0.0 or b.height <= 0.0:
            return False

        return (
            a.x < b.x + b.width
            and b.x < a.x + a.width
            and a.y < b.y + b.height
            and b.y < a.y + a.height
        )
