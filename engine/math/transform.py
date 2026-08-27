from __future__ import annotations

from collections.abc import Callable

from engine.math.vector2d import Vector2D

# Defaults como constantes de modulo, e nao `Vector2D()` escrito na
# assinatura. Sao a MESMA instancia para todo Transform criado sem
# argumento, e isso e inofensivo porque o Vector2D e imutavel --
# ninguem consegue escrever nela. Enquanto o vetor era mutavel esse
# compartilhamento faria mover um no mover todos os outros, e era por
# isso que existia um default_factory.
_ORIGIN = Vector2D(0.0, 0.0)
_UNIT_SCALE = Vector2D(1.0, 1.0)


class Transform:
    """Sistema de coordenadas de um no: posicao, rotacao e escala.

    MUTAVEL de proposito, ao contrario do Vector2D que ele guarda.
    Escrever `no.transform.rotation += x` e a ergonomia que se espera
    de um no de jogo, e congelar o Transform trocaria isso por
    `no.transform = replace(no.transform, ...)` em todo lugar.

    O que a imutabilidade do Vector2D compra aqui e outra coisa: como
    os campos sao valores, TODA alteracao passa por uma atribuicao em
    `Transform` -- e nao mais por um `position.x += 1` que acontecia
    fundo demais para alguem notar. E uma atribuicao E interceptavel:
    e disso que sai o `_on_change`, e com ele o cache de transform
    mundial do Node.

    Por que properties escritas a mao, e nao mais um dataclass
    ---------------------------------------------------------
    A interceptacao precisa custar zero em quem NAO e observado. Um
    `__setattr__` nao consegue: ele intercepta tambem os writes que o
    proprio construtor faz, e `compose()` constroi um Transform por no
    por nivel no caminho de render. Medido: com `__setattr__`, construir
    um Transform passa de 102 ns para 2135 ns -- 20x, pago justamente
    onde o cache ainda nao ajudou.

    Com properties o construtor escreve nos slots privados e nao passa
    por gancho nenhum: construcao continua em ~109 ns, e so quem escreve
    em um campo publico paga (185-279 ns). Ler custa 28 ns em vez de 13,
    o que some ao lado dos ~300 ns de um unico Vector2D.

    O preco e este arquivo: __init__, __eq__ e __repr__ escritos a mao,
    que o dataclass dava de graca. E a troca que um valor com dono
    pede.
    """

    __slots__ = ("_position", "_rotation", "_scale", "_on_change")

    def __init__(
        self,
        position: Vector2D = _ORIGIN,
        rotation: float = 0.0,
        scale: Vector2D = _UNIT_SCALE,
    ) -> None:
        self._position = position
        self._rotation = rotation
        self._scale = scale

        # Aviso de "fiquei velho", para quem depende deste transform.
        # Nasce vazio e SEMPRE nasce vazio: um transform recem-construido
        # nao pertence a ninguem ainda. Quem quiser ser avisado pendura
        # o gancho depois -- e e por isso que copy() e compose(), que
        # constroem, devolvem transforms mudos.
        #
        # E um Callable opaco, e nao uma referencia ao dono, para que o
        # math/ continue sem saber que existe arvore de cena. Daqui ele
        # e so "alguem quis ser avisado".
        self._on_change: Callable[[], None] | None = None

    @property
    def position(self) -> Vector2D:
        return self._position

    @position.setter
    def position(self, value: Vector2D) -> None:
        # Escrever o MESMO valor nao e uma mudanca. Sem esta guarda, um
        # `self.transform.position = origem` incondicional no on_update
        # -- o idioma mais comum que existe -- sujaria a subarvore
        # inteira em todo frame, e o cache nunca acertaria.
        if value == self._position:
            return

        self._position = value

        if self._on_change is not None:
            self._on_change()

    @property
    def rotation(self) -> float:
        return self._rotation

    @rotation.setter
    def rotation(self, value: float) -> None:
        if value == self._rotation:
            return

        self._rotation = value

        if self._on_change is not None:
            self._on_change()

    @property
    def scale(self) -> Vector2D:
        return self._scale

    @scale.setter
    def scale(self, value: Vector2D) -> None:
        if value == self._scale:
            return

        self._scale = value

        if self._on_change is not None:
            self._on_change()

    def __eq__(self, other: object) -> bool:
        # Por valor, e so pelos tres campos: o gancho e quem observa,
        # nao o que o transform vale.
        if not isinstance(other, Transform):
            return NotImplemented

        return (
            self._position == other._position
            and self._rotation == other._rotation
            and self._scale == other._scale
        )

    # Mutavel, logo nao hashavel -- a mesma regra que o dataclass
    # aplicava sozinho. Um Transform como chave de dicionario mudaria
    # de valor debaixo da tabela.
    __hash__ = None  # type: ignore[assignment]

    def __repr__(self) -> str:
        return (
            f"Transform(position={self._position!r}, "
            f"rotation={self._rotation!r}, "
            f"scale={self._scale!r})"
        )

    def copy(self) -> Transform:
        # Rasa, e o bastante: os tres campos sao valores imutaveis, e
        # o unico que precisa ser desamarrado do original e o proprio
        # Transform. O gancho NAO vem junto: a copia e um valor solto,
        # nao o transform local de um no.
        return Transform(self._position, self._rotation, self._scale)

    def compose(self, local: Transform) -> Transform:
        """Aplica `local` por cima de si, tratando `self` como o pai.

        A ordem e escala -> rotacao -> translacao: a posicao local do
        filho e primeiro esticada pela escala do pai, depois girada
        pela rotacao do pai, e so entao somada a posicao do pai. Trocar
        essa ordem faz um filho deslocado orbitar o lugar errado assim
        que o pai gira.

        Guarda a decomposicao (posicao, rotacao, escala) em vez de uma
        matriz. E o mesmo compromisso da `lossyScale` da Unity: exato
        enquanto a escala for uniforme, e sem representar cisalhamento
        quando escala nao-uniforme e rotacao se combinam. Para uma
        engine 2D de pixel art isso nao aparece, e evita carregar uma
        classe de matriz inteira.
        """

        return Transform(
            position=self._position
            + local._position.scaled(self._scale).rotated(self._rotation),
            rotation=self._rotation + local._rotation,
            scale=self._scale.scaled(local._scale),
        )
