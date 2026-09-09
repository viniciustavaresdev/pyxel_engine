"""O contador de frames.

Nada aqui mede tempo, e e esse o ponto: a unidade e o frame, entao um
teste de cooldown e uma sequencia de `tick()` -- deterministica,
instantanea e sem relogio para dessincronizar.
"""

import pytest

from engine.input.key import Key
from engine.runtime.cooldown import Cooldown
from engine.scene.node import Node


class TestItStartsReady:
    """Um no que acaba de entrar na cena pode agir no primeiro frame.

    O contrario -- esperar a propria cadencia antes do primeiro tiro --
    seria uma regra de jogo que o contador estaria inventando sozinho.
    """

    def test_a_fresh_cooldown_is_ready(self):
        assert Cooldown(10).is_ready()

    def test_a_fresh_cooldown_has_nothing_remaining(self):
        assert Cooldown(10).remaining == 0

    def test_waiting_from_the_start_is_one_line(self):
        # Quem quiser o contrario chama start() na construcao da cena, e
        # a intencao fica escrita em vez de embutida no contador.
        cooldown = Cooldown(3)
        cooldown.start()

        assert not cooldown.is_ready()


class TestTheCountdown:
    def test_starting_blocks_it(self):
        cooldown = Cooldown(3)

        cooldown.start()

        assert not cooldown.is_ready()

    def test_it_becomes_ready_after_exactly_duration_ticks(self):
        # O contrato central: nem um frame antes, nem um depois.
        # Errar por um aqui e a diferenca entre 10 e 11 tiros por
        # segundo, que ninguem percebe lendo o codigo e todo mundo
        # percebe jogando.
        cooldown = Cooldown(3)
        cooldown.start()

        cooldown.tick()
        cooldown.tick()
        assert not cooldown.is_ready()

        cooldown.tick()
        assert cooldown.is_ready()

    def test_remaining_counts_down_one_per_tick(self):
        cooldown = Cooldown(3)
        cooldown.start()

        seen = [cooldown.remaining]

        for _ in range(3):
            cooldown.tick()
            seen.append(cooldown.remaining)

        assert seen == [3, 2, 1, 0]

    def test_a_duration_of_one_blocks_a_single_frame(self):
        cooldown = Cooldown(1)
        cooldown.start()

        assert not cooldown.is_ready()

        cooldown.tick()

        assert cooldown.is_ready()

    def test_the_cadence_repeats(self):
        # Uma arma nao dispara uma vez: o ciclo tem de fechar do mesmo
        # jeito na segunda volta.
        cooldown = Cooldown(2)
        fired = []

        for frame in range(9):
            cooldown.tick()

            if cooldown.is_ready():
                fired.append(frame)
                cooldown.start()

        assert fired == [0, 2, 4, 6, 8]


class TestZeroDuration:
    """A aresta que desliga a cadencia sem um `if` em volta de tudo."""

    def test_it_is_ready_from_the_start(self):
        assert Cooldown(0).is_ready()

    def test_it_is_still_ready_right_after_starting(self):
        cooldown = Cooldown(0)

        cooldown.start()

        assert cooldown.is_ready()

    def test_it_never_has_anything_remaining(self):
        cooldown = Cooldown(0)
        cooldown.start()

        assert cooldown.remaining == 0

    def test_it_fires_every_single_frame(self):
        cooldown = Cooldown(0)
        fired = []

        for frame in range(4):
            cooldown.tick()

            if cooldown.is_ready():
                fired.append(frame)
                cooldown.start()

        assert fired == [0, 1, 2, 3]


class TestStartingMidCount:
    """`start()` recomeca do cheio, e nao acumula.

    Acumular faria um gatilho segurado empurrar o proximo tiro para
    sempre: o jogador apertaria mais e atiraria menos.
    """

    def test_it_goes_back_to_full(self):
        cooldown = Cooldown(5)
        cooldown.start()
        cooldown.tick()
        cooldown.tick()

        cooldown.start()

        assert cooldown.remaining == 5

    def test_it_does_not_add_to_what_was_left(self):
        cooldown = Cooldown(5)
        cooldown.start()
        cooldown.tick()

        cooldown.start()

        assert cooldown.remaining != 9
        assert cooldown.remaining == 5

    def test_restarting_every_frame_never_lets_it_finish(self):
        cooldown = Cooldown(2)

        for _ in range(20):
            cooldown.start()
            cooldown.tick()

        assert not cooldown.is_ready()

    def test_starting_an_already_ready_cooldown_blocks_it_again(self):
        cooldown = Cooldown(2)

        assert cooldown.is_ready()
        cooldown.start()

        assert not cooldown.is_ready()


class TestTickingPastReady:
    """Para no zero, em vez de descer para sempre.

    De fora, `is_ready` responderia igual nos dois casos -- e e por
    isso que `remaining` existe: sem ele, um contador que devolvesse
    -4000 depois de um minuto parado seria indistinguivel de um
    correto, ate alguem desenhar uma barra de HUD com ele.
    """

    def test_it_stays_ready(self):
        cooldown = Cooldown(1)
        cooldown.start()

        for _ in range(100):
            cooldown.tick()

        assert cooldown.is_ready()

    def test_remaining_does_not_go_negative(self):
        cooldown = Cooldown(1)
        cooldown.start()

        for _ in range(100):
            cooldown.tick()

        assert cooldown.remaining == 0

    def test_ticking_without_ever_starting_is_harmless(self):
        cooldown = Cooldown(5)

        for _ in range(10):
            cooldown.tick()

        assert cooldown.is_ready()
        assert cooldown.remaining == 0

    def test_a_long_idle_does_not_shorten_the_next_countdown(self):
        # A consequencia pratica do clamp: se a contagem tivesse
        # descido para -100, o proximo start() teria de subir de volta
        # e a cadencia seguinte sairia errada.
        cooldown = Cooldown(3)
        cooldown.start()

        for _ in range(50):
            cooldown.tick()

        cooldown.start()

        assert cooldown.remaining == 3


class TestTheDurationIsATuningLever:
    """O numero que a semana 3 vai passar o tempo todo ajustando.

    Publico e mutavel de proposito -- ajustar tem de ser uma
    atribuicao, nao construir outro cooldown e religar quem o usa.
    """

    def test_it_is_readable(self):
        assert Cooldown(7).duration == 7

    def test_changing_it_affects_the_next_start(self):
        cooldown = Cooldown(3)

        cooldown.duration = 10
        cooldown.start()

        assert cooldown.remaining == 10

    def test_changing_it_does_not_touch_a_running_count(self):
        # Se esticasse a contagem em curso, o efeito de um ajuste
        # dependeria do frame em que ele caiu -- e ajustar numeros de
        # dificuldade com o jogo rodando viraria adivinhacao.
        cooldown = Cooldown(3)
        cooldown.start()
        cooldown.tick()

        cooldown.duration = 100

        assert cooldown.remaining == 2

    def test_a_negative_duration_raises(self):
        # Um cooldown silenciosamente sempre-pronto e o bug que nao da
        # sintoma: a arma atira todo frame e ninguem sabe por que.
        with pytest.raises(ValueError):
            Cooldown(-1)


class TestEachCooldownCountsAlone:
    def test_two_cooldowns_do_not_share_state(self):
        # Erro classico de contador guardado em atributo de classe: dois
        # inimigos com a mesma arma passariam a atirar em uniao.
        first = Cooldown(5)
        second = Cooldown(5)

        first.start()
        first.tick()

        assert second.remaining == 0
        assert second.is_ready()

    def test_the_same_duration_does_not_link_them(self):
        first = Cooldown(3)
        second = Cooldown(3)

        first.start()
        second.start()
        first.tick()

        assert (first.remaining, second.remaining) == (2, 3)


class TestTheIdiomInsideANode:
    """O cooldown dentro do laco de verdade.

    Um `tick()` e UM FRAME, e o contador nao tem como se defender de
    quem chama duas vezes -- e a mesma contrapartida do update sem dt.
    Aqui quem conta os frames e o `update` da arvore, que e o dono
    legitimo dessa contagem.
    """

    def test_a_node_fires_at_its_own_cadence(self, spy_input):
        shots = []

        class Gun(Node):
            def __init__(self, name):
                super().__init__(name)
                self.cooldown = Cooldown(3)
                self.frame = 0

            def on_update(self, input):
                self.cooldown.tick()

                if (
                    input.is_pressed(Key.MOUSE_LEFT)
                    and self.cooldown.is_ready()
                ):
                    shots.append(self.frame)
                    self.cooldown.start()

                self.frame += 1

        root = Node("Root")
        gun = Gun("Gun")
        root.add_child(gun)

        spy_input.press(Key.MOUSE_LEFT)

        for _ in range(10):
            root.update(spy_input)
            spy_input.hold(Key.MOUSE_LEFT)

        # Gatilho segurado dez frames, cadencia de tres: quatro tiros.
        assert shots == [0, 3, 6, 9]

    def test_an_inactive_node_does_not_tick(self, spy_input):
        # Consequencia de o tick morar no on_update: pausar o mundo
        # (`scene.world.active = False`) congela a cadencia junto, sem
        # uma linha a mais. Um contador que se atualizasse sozinho
        # deixaria o inimigo pronto para atirar no frame do despause.
        class Gun(Node):
            def __init__(self, name):
                super().__init__(name)
                self.cooldown = Cooldown(3)

            def on_update(self, input):
                self.cooldown.tick()

        root = Node("Root")
        gun = Gun("Gun")
        root.add_child(gun)
        gun.cooldown.start()

        gun.active = False

        for _ in range(10):
            root.update(spy_input)

        assert gun.cooldown.remaining == 3
