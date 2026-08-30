from __future__ import annotations

from collections.abc import Hashable, Iterable, Mapping
from typing import Generic, TypeVar

from engine.input.key import Key
from engine.math.vector2d import Vector2D
from engine.ports.input import Input

# O nome da acao e do JOGO, nao da engine. `Key` a engine precisa
# possuir -- e o que mantem o `import pyxel` fora do codigo de jogo --,
# mas "pular" e "atacar" sao vocabulario de quem esta sendo escrito, e
# uma engine que enumerasse acoes estaria adivinhando o jogo.
#
# Generico, e nao `str`, para que o jogo possa trazer o proprio Enum:
# com `ActionMap[Action]`, um nome de acao errado vira erro de mypy
# antes de virar erro de execucao. Quem preferir strings usa
# `ActionMap[str]` e paga a diferenca em KeyError.
ActionT = TypeVar("ActionT", bound=Hashable)


class ActionMap(Generic[ActionT]):
    """De teclas para intencoes.

    Codigo de jogo que pergunta `is_pressed(Key.LEFT) or
    is_pressed(Key.A)` esta enumerando teclas onde queria nomear uma
    intencao -- e a lista se repete em todo lugar que precisa dela.
    Aqui a lista mora em um lugar so, e as consequencias vem juntas:
    remapear controle e reescrever uma entrada do mapa, e o mapa e
    testavel sem backend nenhum, porque so fala com a porta `Input`.

    O mapa NAO guarda o input: ele recebe um a cada pergunta. Sem
    estado proprio alem das amarracoes, o mesmo mapa serve a arvore
    inteira e continua respondendo pelo frame que o laco esta passando,
    sem nenhuma sincronia para manter.
    """

    def __init__(
        self, bindings: Mapping[ActionT, Iterable[Key]] | None = None
    ) -> None:
        self._bindings: dict[ActionT, frozenset[Key]] = {}

        if bindings is not None:
            for action, keys in bindings.items():
                self.bind(action, keys)

    # Bindings
    def bind(self, action: ActionT, keys: Iterable[Key]) -> None:
        """Amarra uma acao a um conjunto de teclas, substituindo o
        anterior.

        Substituir, e nao acumular: e a operacao que uma tela de
        remapeamento faz, e acumular deixaria a tecla antiga
        respondendo junto com a nova -- exatamente o que o jogador
        pediu para nao acontecer. Somar teclas continua possivel,
        passando o conjunto inteiro.
        """
        self._bindings[action] = frozenset(keys)

    def keys_for(self, action: ActionT) -> frozenset[Key]:
        """As teclas de uma acao. Congelado: o mapa muda por `bind`."""
        return self._keys(action)

    def __contains__(self, action: object) -> bool:
        return action in self._bindings

    def _keys(self, action: ActionT) -> frozenset[Key]:
        keys = self._bindings.get(action)

        if keys is None:
            # Levanta em vez de devolver "nao pressionada". Uma acao
            # inexistente e erro de programacao -- um nome digitado
            # errado --, e o silencio daria um controle que nunca
            # responde, sem uma linha de erro para procurar.
            raise KeyError(f"Action is not bound in this map: {action!r}")

        return keys

    # Queries
    def is_pressed(self, action: ActionT, input: Input) -> bool:
        """Alguma tecla da acao esta baixa agora."""
        return any(input.is_pressed(key) for key in self._keys(action))

    def is_just_pressed(self, action: ActionT, input: Input) -> bool:
        """A ACAO passou a valer neste frame.

        Nao e "alguma tecla desceu neste frame", e a diferenca aparece
        com acao de mais de uma tecla: segurando ESPACO e tocando Z, o
        pulo dispararia de novo com o jogador ja no ar. A acao ja
        estava valendo; o que mudou foi so por qual tecla.

        A pergunta e respondida sem memoria de frame: uma tecla baixa
        que NAO desceu agora ja estava baixa antes.
        """
        became_active = False

        for key in self._keys(action):
            if input.is_just_pressed(key):
                became_active = True
            elif input.is_pressed(key):
                return False

        return became_active

    def is_just_released(self, action: ActionT, input: Input) -> bool:
        """A ACAO deixou de valer neste frame.

        O espelho do caso acima: soltar ESPACO com o Z ainda baixo nao
        solta o tiro carregado, porque a acao continua valendo.
        """
        became_inactive = False

        for key in self._keys(action):
            if input.is_pressed(key):
                return False

            if input.is_just_released(key):
                became_inactive = True

        return became_inactive

    def get_axis(
        self, negative: ActionT, positive: ActionT, input: Input
    ) -> float:
        """-1, 0 ou +1 a partir de duas acoes opostas.

        As duas ao mesmo tempo dao zero -- se anulam. A alternativa
        ("a ultima vence") exige lembrar qual desceu antes, e um eixo
        com memoria e um eixo que discorda do teclado depois de uma
        pausa ou de uma troca de cena.
        """
        return float(self.is_pressed(positive, input)) - float(
            self.is_pressed(negative, input)
        )

    def get_vector(
        self,
        left: ActionT,
        right: ActionT,
        up: ActionT,
        down: ActionT,
        input: Input,
    ) -> Vector2D:
        """Direcao de movimento, ja NORMALIZADA.

        Normalizar aqui e o ponto: a soma de dois eixos tem modulo
        1,41 na diagonal, e todo jogo que esquece disso anda 41% mais
        rapido na diagonal. Nada pressionado devolve o vetor zero, que
        `normalized()` preserva.

        Y cresce para BAIXO, como na tela: `up` empurra para -1.
        """
        return Vector2D(
            self.get_axis(left, right, input),
            self.get_axis(up, down, input),
        ).normalized()
