from __future__ import annotations

import math
from collections.abc import Collection

from engine.math.rect import Rect
from engine.math.vector2d import Vector2D
from engine.physics.raycast_hit import RaycastHit
from engine.ports.tile_source import TileSource
from engine.scene.body import Body

# Quanto a caixa encolhe, de cada lado, antes de virar indice de celula.
#
# Existe por causa do acumulo de float. Um corpo empurrado dez vezes
# contra a mesma parede termina com a borda em 16.0000001, e nao em
# 16.0 -- e `floor(16.0000001 / 8)` e a coluna 2, a da parede. A
# partir dai o corpo "ja esta" na parede, a coluna deixa de ser nova
# para o move_and_slide, e ele atravessa. Um milionesimo de pixel
# esta muitas ordens de grandeza abaixo de qualquer coisa que a tela
# mostre, e e o que torna a borda imune a deriva.
_EPSILON = 1e-6


class Collision:
    """Geometria contra o mundo: caixas contra a grade de tiles.

    Duas metades que nao se parecem, e e de proposito. Paredes sao
    milhares de celulas que nunca mudam e se acham por DIVISAO pelo
    tamanho do tile; corpos sao uns dez, mudam todo frame, e se acham
    percorrendo a lista. Uma parede nunca entra na lista de corpos, e e
    isso que apaga a pergunta do quadtree: a coisa numerosa e uma grade,
    e uma grade se indexa.

    O que NAO entra aqui: nada que saiba o que e um jogador, uma bala
    ou um inimigo -- e nem a decisao de qual tile e parede, que e do
    jogo e chega pronta pelo construtor. Corpo, caixa, grade e raio.
    """

    def __init__(
        self,
        tiles: TileSource,
        solid: Collection[tuple[int, int]],
    ) -> None:
        self._tiles = tiles

        # Copiado para um frozenset: a pergunta "e solido?" e feita
        # varias vezes por eixo por frame, e um `in` sobre lista seria
        # linear no tamanho do conjunto. O jogo passa o que quiser.
        self._solid = frozenset(solid)

        # A outra metade: os corpos. Uma lista, e forca bruta sobre
        # ela -- sao uns dez, e e isso que apaga o quadtree. Uma parede
        # nunca entra aqui.
        self._bodies: list[Body] = []

    @property
    def tile_size(self) -> int:
        return self._tiles.tile_size

    # Corpos
    @property
    def bodies(self) -> tuple[Body, ...]:
        """Os corpos registrados, na ordem em que entraram.

        Tupla, e nao a lista: quem quiser mudar o conjunto passa por
        `add_body` / `remove_body`, e nao ha como um chamador guardar a
        lista viva e ve-la mudar embaixo dele no meio de um percurso.
        """
        return tuple(self._bodies)

    def add_body(self, body: Body) -> None:
        """Registra um corpo para `bodies_in` e `raycast` o enxergarem.

        `move_and_slide` NAO exige registro: mover contra a grade e uma
        pergunta sobre o proprio corpo, e um corpo que so precisa nao
        atravessar parede nao tem por que ser visto por raio nenhum.
        Registrar e dizer "os outros podem me acertar".

        A lista e mantida pelo JOGO, e isso e uma divida declarada: um
        corpo que sai da arvore por `queue_free()` e continua aqui e
        um fantasma que ainda para bala. Os grupos da semana 3 apoiam
        essa lista na arvore, que e a fonte da verdade; ate la, quem
        registra tem de desregistrar. Idempotente: registrar duas vezes
        nao duplica -- um corpo em dobro seria acertado duas vezes.
        """
        if body not in self._bodies:
            self._bodies.append(body)

    def remove_body(self, body: Body) -> None:
        """Tira o corpo da lista. Um corpo que nao esta nela e no-op."""
        if body in self._bodies:
            self._bodies.remove(body)

    def bodies_in(self, area: Rect) -> list[Body]:
        """Os corpos cuja caixa sobrepoe `area`.

        Forca bruta, de proposito: com dez corpos nao ha o que
        otimizar, e o `Rect.intersects` ja responde com a regra
        semiaberta -- encostar nao e estar dentro, e um corpo de area
        zero nunca esta em lugar nenhum.

        Uma lista nova a cada chamada, na ordem de registro. O chamador
        pode mata-la a vontade.
        """
        return [
            body
            for body in self._bodies
            if area.intersects(body.get_world_bounds())
        ]

    # Grade
    def cell_at(self, point: Vector2D) -> tuple[int, int]:
        """A celula que contem um ponto do mundo.

        A conta mundo -> celula, escrita UMA vez: divide pelo tamanho
        do tile e arredonda PARA BAIXO. `int()` trunca em direcao ao
        zero, e em coordenada negativa erraria de celula -- (-0.5)
        cairia na coluna 0 em vez de na -1. E a mesma regra semiaberta
        do Rect vista do lado da grade: um ponto exatamente sobre a
        divisa pertence a celula da direita, e a nenhuma outra.
        """
        size = self._tiles.tile_size

        return (math.floor(point.x / size), math.floor(point.y / size))

    def is_solid(self, column: int, row: int) -> bool:
        """A celula e parede?

        FORA DO MAPA E SOLIDO. E a unica decisao que a engine toma sobre
        o que existe alem da borda, e ela e tomada aqui, olhando para
        `width` e `height` -- e nao herdada do backend, que responderia
        `(0, 0)` e deixaria "fora do mapa" e "chao" serem a mesma coisa.
        A alternativa, "fora e vazio", deixaria um corpo sair do mundo
        e nunca mais achar o caminho de volta pela grade.
        """
        if not (
            0 <= column < self._tiles.width and 0 <= row < self._tiles.height
        ):
            return True

        return self._tiles.get_tile(column, row) in self._solid

    # Movimento
    def move_and_slide(self, body: Body, delta: Vector2D) -> None:
        """Move o corpo por `delta`, parando na primeira parede de cada
        eixo.

        RESOLVE POR EIXO, nao pelo vetor. Move X e empurra para fora
        das celulas solidas que a caixa invadiu; depois Y, e empurra de
        novo. E o que da deslizar na parede de graca: na diagonal
        contra uma parede vertical o X e barrado e o Y passa. Resolver
        o vetor inteiro exigiria normal de contato e projecao -- mais
        matematica para um resultado pior em caixas alinhadas aos
        eixos.

        So as celulas RECEM-ENTRADAS contam. Cada eixo compara as
        colunas (ou linhas) que a caixa cobria antes do passo com as
        que cobre depois, e consulta apenas as novas. Tres coisas saem
        disso, e as tres sao o que separa um HM que desliza de um que
        gruda na quina:

        - Parado colado na parede nao ha celula nova, entao nao ha
          empurrao fantasma todo frame. O intervalo semiaberto do Rect
          ja dizia que encostar nao e sobrepor; aqui a grade concorda.
        - Um delta maior que um tile ve TODAS as colunas que cruzou,
          entao um corpo rapido nao atravessa parede fina. Isto vale
          para corpos; a bala, que e mais fina e mais rapida, usa
          `raycast` pelo mesmo motivo.
        - Um corpo que ja nasceu dentro de parede NAO e ejetado. As
          celulas dele nao sao novas, e nao ha direcao certa para
          empurrar quem ja esta do outro lado. move_and_slide impede
          ENTRAR; sair de onde nunca se deveria estar e do jogo.

        Escreve em `body.transform.position`, que e LOCAL, e resolve
        em coordenadas de MUNDO. Isso so fecha se o referencial do pai
        for uma translacao pura -- que e o caso da camada `world` e de
        qualquer no que so posicione filhos. Um corpo pendurado em um
        pai girado ou escalado teria o empurrao aplicado no eixo
        errado; e um arranjo que nenhum jogo de tiles pede, e o preco
        de suporta-lo seria inverter a transform do pai a cada passo.
        """
        # Area zero nao colide com nada -- a mesma regra do
        # Rect.intersects, pelo mesmo motivo: uma caixa vazia nao contem
        # ponto nenhum. Um no sem tamanho e um marco de spawn, e passa.
        bounds = body.get_world_bounds().normalized()

        if bounds.width <= 0.0 or bounds.height <= 0.0:
            body.transform.position = body.transform.position + delta
            return

        if delta.x != 0.0:
            self._move_axis(body, delta.x, axis=0)

        if delta.y != 0.0:
            self._move_axis(body, delta.y, axis=1)

    def _move_axis(self, body: Body, amount: float, axis: int) -> None:
        before = self._span(body.get_world_bounds(), axis)

        self._shift(body, amount, axis)

        bounds = body.get_world_bounds().normalized()
        after = self._span(bounds, axis)

        # As celulas do OUTRO eixo que a caixa cobre neste passo: para
        # um passo em X sao as linhas, para um passo em Y as colunas.
        across = self._span(bounds, 1 - axis)

        size = self._tiles.tile_size

        if amount > 0.0:
            # Entrando pela direita/baixo. As celulas novas vao da
            # primeira depois da antiga borda ate a nova borda; a mais
            # proxima e a menor, e a borda dianteira para na face dela.
            for cell in range(before[1] + 1, after[1] + 1):
                if self._any_solid(cell, across, axis):
                    face = float(cell * size)
                    self._shift(body, face - _high(bounds, axis), axis)
                    return
        else:
            # Entrando pela esquerda/cima. A mais proxima e a maior, e o
            # limite e a face de tras dela.
            for cell in range(before[0] - 1, after[0] - 1, -1):
                if self._any_solid(cell, across, axis):
                    face = float((cell + 1) * size)
                    self._shift(body, face - _low(bounds, axis), axis)
                    return

    # Raio
    def raycast(
        self,
        origin: Vector2D,
        direction: Vector2D,
        max_distance: float,
        ignore: Collection[Body] = (),
    ) -> RaycastHit | None:
        """O primeiro solido -- parede ou corpo -- na direcao dada.

        PERCORRE A GRADE, nao testa tudo. DDA (Amanatides & Woo): avanca
        celula a celula na direcao do raio, sempre pela divisa mais
        proxima, e para na primeira solida. O custo e proporcional a
        distancia percorrida, nao ao tamanho do mapa -- um raio de 100
        px toca no maximo uns 25 tiles num mapa de 65 mil.

        Os corpos entram por teste de fatias (slab) contra a caixa de
        cada um, e vence o acerto mais proximo. No EMPATE a parede
        vence: um corpo encostado na parede pelo lado de la nao e
        atingido, porque a bala parou na parede antes.

        Tres decisoes de borda, todas com teste:

        - Um raio que NASCE dentro de solido -- celula, corpo, ou fora
          do mapa -- acerta na origem, a distancia zero e com normal
          zero. Nao ha face para nomear. E o que faz a bala da semana
          3 funcionar como o plano pede: um raio da posicao anterior
          ate a nova, todo frame, e se a anterior ja estava na parede
          o tiro acabou no frame passado.
        - `direction` e NORMALIZADA aqui, entao `distance` esta sempre
          em unidades de mundo. Direcao zero levanta: nao ha raio sem
          direcao, e devolver None esconderia um bug de quem chamou.
        - As bordas sao as do Rect, semiabertas: um raio que passa
          exatamente sobre a face de baixo ou da direita de um corpo
          nao o toca; sobre a de cima ou da esquerda, toca. E a mesma
          regra que decide que um ponto sobre a divisa cai em um tile
          so.

        `ignore` existe porque o inimigo lanca o raio de dentro da
        propria caixa, e sem isso acertaria a si mesmo no primeiro
        pixel. Uma colecao, e nao um corpo: a bala vai querer ignorar
        quem atirou e a si mesma.
        """
        if direction.x == 0.0 and direction.y == 0.0:
            raise ValueError("A ray needs a direction.")

        direction = direction.normalized()

        hit = self._raycast_grid(origin, direction, max_distance)

        # Estrito: no empate o que ja esta em `hit` fica -- a parede
        # contra um corpo, e o corpo registrado antes contra o de
        # depois.
        for body in self._bodies:
            if body in ignore:
                continue

            candidate = self._raycast_body(
                origin, direction, max_distance, body
            )

            if candidate is None:
                continue

            if hit is None or candidate.distance < hit.distance:
                hit = candidate

        return hit

    def _raycast_grid(
        self, origin: Vector2D, direction: Vector2D, max_distance: float
    ) -> RaycastHit | None:
        size = self._tiles.tile_size
        column, row = self.cell_at(origin)

        if self.is_solid(column, row):
            return RaycastHit(origin, Vector2D(), 0.0, None)

        # Por eixo: o passo (+1/-1/0), a distancia ao longo do raio ate
        # a PROXIMA divisa, e quanto cada divisa seguinte acrescenta.
        # Um eixo parado (direcao zero nele) nunca avanca: sua proxima
        # divisa fica no infinito.
        step_x, t_max_x, t_delta_x = _axis_setup(
            origin.x, direction.x, column, size
        )
        step_y, t_max_y, t_delta_y = _axis_setup(
            origin.y, direction.y, row, size
        )

        while True:
            # A divisa mais proxima decide o eixo. No empate exato -- o
            # raio passa por um canto -- Y avanca primeiro e X logo em
            # seguida, a mesma distancia; a celula diagonal e visitada
            # em dois passos e continua sendo acertada se for solida.
            if t_max_x < t_max_y:
                distance = t_max_x
                column += step_x
                normal = Vector2D(float(-step_x), 0.0)
                t_max_x += t_delta_x
            else:
                distance = t_max_y
                row += step_y
                normal = Vector2D(0.0, float(-step_y))
                t_max_y += t_delta_y

            if distance > max_distance:
                return None

            if self.is_solid(column, row):
                return RaycastHit(
                    origin + direction * distance, normal, distance, None
                )

    def _raycast_body(
        self,
        origin: Vector2D,
        direction: Vector2D,
        limit: float,
        body: Body,
    ) -> RaycastHit | None:
        bounds = body.get_world_bounds().normalized()

        # Area zero nao e atingivel, pela regra do Rect: nao contem
        # ponto nenhum, entao nenhum ponto do raio esta nela.
        if bounds.width <= 0.0 or bounds.height <= 0.0:
            return None

        # Slab: o raio esta dentro da caixa no intervalo [t_min, t_max]
        # em que esta dentro das DUAS faixas, a de X e a de Y. A
        # entrada e a maior das duas entradas; a saida, a menor das
        # duas saidas. Se a entrada vem depois da saida, errou.
        t_min = 0.0
        t_max = math.inf
        normal = Vector2D()

        for axis in (0, 1):
            low = _low(bounds, axis)
            high = _high(bounds, axis)
            start = origin.x if axis == 0 else origin.y
            speed = direction.x if axis == 0 else direction.y

            if speed == 0.0:
                # Paralelo a esta faixa: ou esta dentro dela o tempo
                # todo, ou nunca. Semiaberto, como o Rect.contains.
                if not (low <= start < high):
                    return None

                continue

            enter = (low - start) / speed
            leave = (high - start) / speed

            if enter > leave:
                enter, leave = leave, enter

            if enter > t_min:
                # Esta faixa e a que decide a entrada: a normal e a face
                # dela pela qual o raio entrou, virada contra o raio.
                t_min = enter
                sign = 1.0 if speed > 0.0 else -1.0
                normal = (
                    Vector2D(-sign, 0.0) if axis == 0 else Vector2D(0.0, -sign)
                )

            t_max = min(t_max, leave)

            if t_min > t_max:
                return None

        # A saida em `high` e EXCLUSIVA: um raio que toca a caixa so no
        # ponto de saida (entra e sai a mesma distancia, na face de
        # fora) nao a acertou. Comparado com a saida da CAIXA, e nao
        # com o alcance: um corpo exatamente em `limit` e atingido.
        if t_min == t_max and t_min > 0.0:
            return None

        if t_min > limit:
            return None

        return RaycastHit(origin + direction * t_min, normal, t_min, body)

    def _span(self, bounds: Rect, axis: int) -> tuple[int, int]:
        # Primeira e ultima celula que a caixa toca neste eixo, com a
        # borda de fora EXCLUIDA: e a regra semiaberta do Rect levada a
        # grade. Uma caixa com a borda direita em 16.0 cobre a coluna
        # 1, e nao a 2 -- encostada, nao sobreposta. O epsilon e o que
        # mantem isso verdade depois de dez empurroes com erro de float.
        bounds = bounds.normalized()
        size = self._tiles.tile_size

        low = _low(bounds, axis) + _EPSILON
        high = _high(bounds, axis) - _EPSILON

        return (math.floor(low / size), math.floor(high / size))

    def _any_solid(
        self, cell: int, across: tuple[int, int], axis: int
    ) -> bool:
        for other in range(across[0], across[1] + 1):
            column, row = (cell, other) if axis == 0 else (other, cell)

            if self.is_solid(column, row):
                return True

        return False

    @staticmethod
    def _shift(body: Body, amount: float, axis: int) -> None:
        step = Vector2D(amount, 0.0) if axis == 0 else Vector2D(0.0, amount)

        body.transform.position = body.transform.position + step


def _axis_setup(
    start: float, speed: float, cell: int, size: int
) -> tuple[int, float, float]:
    """O estado do DDA em um eixo: passo, proxima divisa, e o intervalo.

    Devolve (step, t_max, t_delta). `t_max` e a distancia ao longo do
    raio ate a proxima divisa deste eixo; `t_delta`, quanto cada divisa
    seguinte acrescenta -- um tile inteiro dividido pela componente da
    direcao. Eixo parado nao avanca nunca: passo zero e divisa no
    infinito, e o `<` do laco sempre escolhe o outro.

    Nascer exatamente sobre uma divisa e o caso que vale conferir:
    indo para a direita a partir de x = 16, a celula e a 2 (semiaberto)
    e a proxima divisa esta a 8; indo para a ESQUERDA a partir do mesmo
    ponto, a proxima divisa esta a distancia ZERO -- o raio ja esta na
    face da celula 1, e entra nela no primeiro passo. Se ela for
    solida, o acerto e na origem com normal (+1, 0): encostado na
    parede, olhando para ela.
    """
    if speed > 0.0:
        return 1, ((cell + 1) * size - start) / speed, size / speed

    if speed < 0.0:
        return -1, (cell * size - start) / speed, size / -speed

    return 0, math.inf, math.inf


def _low(bounds: Rect, axis: int) -> float:
    return bounds.x if axis == 0 else bounds.y


def _high(bounds: Rect, axis: int) -> float:
    return bounds.x + bounds.width if axis == 0 else bounds.y + bounds.height
