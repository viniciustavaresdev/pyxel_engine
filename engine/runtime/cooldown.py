from __future__ import annotations


class Cooldown:
    """Um contador em FRAMES que sabe responder "ja?".

    Consequencia direta de aposentar o `dt`: sem relogio, "meio
    segundo" nao e uma quantidade que a engine saiba medir, e a unidade
    que sobra -- a unica que o laco realmente conta -- e o frame. A
    30 fps, `Cooldown(15)` e meio segundo; trocar o `fps` do
    `ApplicationConfig` muda essa equivalencia junto com todo o resto,
    que e o preco ja declarado de nao medir tempo.

    Pequeno de proposito. NAO e um agendador: nao guarda callback, nao
    dispara nada sozinho, nao sabe o que e uma arma nem o que e um
    inimigo. Quem pergunta e quem age; ele so conta.

    O idioma e este, e sao duas linhas no on_update:

        self.cooldown.tick()

        if disparou and self.cooldown.is_ready():
            self.atirar()
            self.cooldown.start()

    Nasce PRONTO. Um no que acaba de entrar na cena pode agir no
    primeiro frame -- uma arma que precisasse esperar a propria
    cadencia antes do primeiro tiro seria uma regra de jogo que o
    contador estaria inventando sozinho. Quem quiser o contrario
    chama `start()` no on_enter, e a intencao fica escrita.

    Um `tick()` e UM FRAME, e disso ele nao tem como se defender:
    chamado duas vezes no mesmo frame, a cadencia dobra. E a mesma
    contrapartida do `update` sem dt -- quem conta os frames e o laco,
    nao o contador.
    """

    __slots__ = ("duration", "_remaining")

    def __init__(self, duration: int) -> None:
        if duration < 0:
            # Levanta, em vez de tratar como zero. Uma duracao negativa
            # e erro de programacao -- um numero que veio de uma
            # subtracao que passou do ponto --, e um cooldown
            # silenciosamente sempre-pronto e exatamente o bug que nao
            # da sintoma: a arma atira todo frame e ninguem sabe por que.
            raise ValueError(
                f"Cooldown duration cannot be negative: {duration}"
            )

        # Publica e mutavel de proposito. O tempo de reacao do inimigo
        # e a cadencia de tiro sao os numeros que mais vao ser mexidos,
        # e mexe-los tem de ser uma atribuicao. Vale a partir do
        # PROXIMO start(): mudar a duracao no meio de uma contagem nao
        # estica nem encurta a que ja esta correndo, senao o efeito de
        # um ajuste dependeria do frame em que ele caiu.
        self.duration = duration

        self._remaining = 0

    @property
    def remaining(self) -> int:
        """Quantos frames faltam. Zero quando esta pronto.

        Somente leitura: contagem se comeca com `start()`. Existe por
        dois motivos concretos -- e o que um HUD desenha como barra, e
        e o unico jeito de um teste distinguir "parou no zero" de
        "continuou descendo para sempre", que de fora respondem igual.
        """
        return self._remaining

    def start(self) -> None:
        """Comeca (ou recomeca) a contagem, do cheio.

        RECOMECA, e nao acumula: chamado no meio de uma contagem, volta
        para `duration` em vez de somar. Acumular faria um gatilho
        segurado empurrar o proximo tiro para sempre -- o jogador
        apertaria mais e atiraria menos.
        """
        self._remaining = self.duration

    def tick(self) -> None:
        """Passou um frame.

        Parado no zero, e nao descendo para sempre. A diferenca nao
        aparece em `is_ready`, mas aparece em `remaining` -- e um
        contador que devolve -4000 depois de um minuto parado nao e um
        numero que alguem queira ler num HUD ou num breakpoint.
        """
        if self._remaining > 0:
            self._remaining -= 1

    def is_ready(self) -> bool:
        """Ja pode agir?

        Duracao zero responde True sempre, inclusive logo depois de um
        `start()`. E a aresta que importa: e assim que se desliga uma
        cadencia sem escrever um `if` em volta de toda chamada.
        """
        return self._remaining <= 0
