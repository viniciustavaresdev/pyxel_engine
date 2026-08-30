from enum import Enum, auto

import pytest

from engine.input.action_map import ActionMap
from engine.input.key import Key
from engine.scene.node import Node
from tests.conftest import SpyInput


class Action(Enum):
    """O vocabulario de um jogo imaginario.

    Fica no TESTE, e nao na engine, de proposito: e a demonstracao de
    que o mapa nao conhece acao nenhuma de antemao -- ele so guarda as
    que lhe deram.
    """

    MOVE_LEFT = auto()
    MOVE_RIGHT = auto()
    MOVE_UP = auto()
    MOVE_DOWN = auto()
    JUMP = auto()


def movement_map():
    return ActionMap(
        {
            Action.MOVE_LEFT: {Key.LEFT, Key.A},
            Action.MOVE_RIGHT: {Key.RIGHT, Key.D},
            Action.MOVE_UP: {Key.UP, Key.W},
            Action.MOVE_DOWN: {Key.DOWN, Key.S},
        }
    )


class TestBindings:

    def test_the_constructor_accepts_any_iterable_of_keys(self):
        actions = ActionMap(
            {
                Action.JUMP: [Key.SPACE, Key.Z],
                Action.MOVE_LEFT: (Key.LEFT,),
            }
        )

        assert actions.keys_for(Action.JUMP) == frozenset({Key.SPACE, Key.Z})
        assert actions.keys_for(Action.MOVE_LEFT) == frozenset({Key.LEFT})

    def test_bind_replaces_instead_of_accumulating(self):
        # E a operacao de uma tela de remapeamento: a tecla antiga tem
        # de parar de responder, senao o jogador remapeou e continua com
        # o controle anterior ativo.
        actions = ActionMap({Action.JUMP: {Key.SPACE}})

        actions.bind(Action.JUMP, {Key.Z})

        assert actions.keys_for(Action.JUMP) == frozenset({Key.Z})

    def test_an_empty_map_binds_nothing(self):
        # Parametrizado no tipo da acao mesmo vazio: sem as bindings
        # nao ha de onde inferir, e um `ActionMap()` cru vira
        # `ActionMap[Never]` -- que so recusa acoes, e no mypy.
        actions: ActionMap[Action] = ActionMap()

        assert Action.JUMP not in actions

    def test_contains_answers_for_a_bound_action(self):
        actions = ActionMap({Action.JUMP: {Key.SPACE}})

        assert Action.JUMP in actions
        assert Action.MOVE_LEFT not in actions

    def test_the_returned_key_set_is_frozen(self):
        actions = ActionMap({Action.JUMP: {Key.SPACE}})

        assert isinstance(actions.keys_for(Action.JUMP), frozenset)

    def test_string_names_work_too(self):
        # O mapa e generico no tipo da acao. Um Enum proprio da erro de
        # mypy quando o nome esta errado; string da KeyError. As duas
        # opcoes existem, e a escolha e de quem escreve o jogo.
        actions = ActionMap({"jump": {Key.SPACE}})
        input = SpyInput()
        input.press(Key.SPACE)

        assert actions.is_pressed("jump", input)


class TestAnUnboundActionRaises:
    """Silencio aqui daria um controle que nunca responde.

    Devolver False para uma acao inexistente e o modo de falha mais
    caro que este mapa poderia ter: o jogo roda, o botao nao faz nada,
    e nao ha uma linha de erro para procurar. As quatro perguntas
    levantam.
    """

    def empty(self) -> ActionMap[Action]:
        return ActionMap()

    def test_is_pressed_raises(self):
        with pytest.raises(KeyError):
            self.empty().is_pressed(Action.JUMP, SpyInput())

    def test_is_just_pressed_raises(self):
        with pytest.raises(KeyError):
            self.empty().is_just_pressed(Action.JUMP, SpyInput())

    def test_is_just_released_raises(self):
        with pytest.raises(KeyError):
            self.empty().is_just_released(Action.JUMP, SpyInput())

    def test_get_axis_raises(self):
        with pytest.raises(KeyError):
            self.empty().get_axis(
                Action.MOVE_LEFT, Action.MOVE_RIGHT, SpyInput()
            )

    def test_keys_for_raises(self):
        with pytest.raises(KeyError):
            self.empty().keys_for(Action.JUMP)

    def test_the_message_names_the_action(self):
        # A mensagem tem de dizer QUAL acao, senao o KeyError so move o
        # problema de "nao responde" para "levantou em algum lugar".
        with pytest.raises(KeyError, match="JUMP"):
            self.empty().is_pressed(Action.JUMP, SpyInput())


class TestIsPressed:

    def test_any_bound_key_activates_the_action(self):
        actions = movement_map()

        for key in (Key.LEFT, Key.A):
            input = SpyInput()
            input.press(key)

            assert actions.is_pressed(Action.MOVE_LEFT, input)

    def test_an_unrelated_key_does_not(self):
        actions = movement_map()
        input = SpyInput()
        input.press(Key.RIGHT)

        assert not actions.is_pressed(Action.MOVE_LEFT, input)

    def test_an_action_bound_to_nothing_is_never_pressed(self):
        # Amarrada ao conjunto vazio e diferente de nao amarrada: e um
        # controle desligado de proposito, e responde False em vez de
        # levantar.
        actions = ActionMap({Action.JUMP: set()})
        input = SpyInput()
        input.press(Key.SPACE)

        assert not actions.is_pressed(Action.JUMP, input)


class TestIsJustPressed:
    """A acao passou a valer neste frame -- nao "alguma tecla desceu"."""

    def test_fires_on_the_frame_the_key_goes_down(self):
        actions = ActionMap({Action.JUMP: {Key.SPACE, Key.Z}})
        input = SpyInput()

        input.press(Key.SPACE)

        assert actions.is_just_pressed(Action.JUMP, input)

    def test_does_not_fire_while_the_key_is_held(self):
        actions = ActionMap({Action.JUMP: {Key.SPACE, Key.Z}})
        input = SpyInput()
        input.press(Key.SPACE)

        input.hold(Key.SPACE)

        assert not actions.is_just_pressed(Action.JUMP, input)

    def test_a_second_bound_key_does_not_fire_the_action_again(self):
        # O caso que separa "acao" de "tecla": com ESPACO segurado,
        # tocar Z dispararia um segundo pulo com o jogador ja no ar.
        actions = ActionMap({Action.JUMP: {Key.SPACE, Key.Z}})
        input = SpyInput()
        input.press(Key.SPACE)
        input.hold(Key.SPACE)

        input.press(Key.Z)

        assert input.is_just_pressed(Key.Z)
        assert not actions.is_just_pressed(Action.JUMP, input)

    def test_fires_again_after_the_action_fully_ends(self):
        actions = ActionMap({Action.JUMP: {Key.SPACE, Key.Z}})
        input = SpyInput()
        input.press(Key.SPACE)
        input.release(Key.SPACE)

        input.press(Key.Z)

        assert actions.is_just_pressed(Action.JUMP, input)

    def test_two_bound_keys_going_down_together_fire_once(self):
        actions = ActionMap({Action.JUMP: {Key.SPACE, Key.Z}})
        input = SpyInput()

        input.press(Key.SPACE)
        input.press(Key.Z)

        assert actions.is_just_pressed(Action.JUMP, input) is True


class TestIsJustReleased:
    """O espelho: a acao deixou de valer neste frame."""

    def test_fires_when_the_only_key_comes_up(self):
        actions = ActionMap({Action.JUMP: {Key.SPACE}})
        input = SpyInput()
        input.press(Key.SPACE)

        input.release(Key.SPACE)

        assert actions.is_just_released(Action.JUMP, input)

    def test_does_not_fire_while_another_bound_key_is_still_down(self):
        # Soltar ESPACO com Z ainda baixo nao solta o tiro carregado: a
        # acao continua valendo.
        actions = ActionMap({Action.JUMP: {Key.SPACE, Key.Z}})
        input = SpyInput()
        input.press(Key.SPACE)
        input.press(Key.Z)
        input.hold(Key.Z)

        input.release(Key.SPACE)

        assert input.is_just_released(Key.SPACE)
        assert not actions.is_just_released(Action.JUMP, input)

    def test_fires_when_the_last_key_comes_up(self):
        actions = ActionMap({Action.JUMP: {Key.SPACE, Key.Z}})
        input = SpyInput()
        input.press(Key.SPACE)
        input.press(Key.Z)
        input.release(Key.SPACE)

        input.release(Key.Z)

        assert actions.is_just_released(Action.JUMP, input)

    def test_does_not_fire_when_nothing_was_touched(self):
        actions = ActionMap({Action.JUMP: {Key.SPACE}})

        assert not actions.is_just_released(Action.JUMP, SpyInput())


class TestGetAxis:

    def test_positive_action_gives_one(self):
        actions = movement_map()
        input = SpyInput()
        input.press(Key.D)

        axis = actions.get_axis(Action.MOVE_LEFT, Action.MOVE_RIGHT, input)

        assert axis == 1.0

    def test_negative_action_gives_minus_one(self):
        actions = movement_map()
        input = SpyInput()
        input.press(Key.A)

        axis = actions.get_axis(Action.MOVE_LEFT, Action.MOVE_RIGHT, input)

        assert axis == -1.0

    def test_nothing_pressed_gives_zero(self):
        actions = movement_map()

        axis = actions.get_axis(
            Action.MOVE_LEFT, Action.MOVE_RIGHT, SpyInput()
        )

        assert axis == 0.0

    def test_both_directions_cancel(self):
        # Sem memoria de qual desceu antes: um eixo com memoria e um
        # eixo que discorda do teclado depois de uma pausa.
        actions = movement_map()
        input = SpyInput()
        input.press(Key.A)
        input.press(Key.D)

        axis = actions.get_axis(Action.MOVE_LEFT, Action.MOVE_RIGHT, input)

        assert axis == 0.0

    def test_the_axis_ignores_which_bound_key_did_it(self):
        actions = movement_map()

        for key in (Key.LEFT, Key.A):
            input = SpyInput()
            input.press(key)

            assert (
                actions.get_axis(Action.MOVE_LEFT, Action.MOVE_RIGHT, input)
                == -1.0
            )


class TestGetVector:

    def _vector(self, actions, input):
        return actions.get_vector(
            Action.MOVE_LEFT,
            Action.MOVE_RIGHT,
            Action.MOVE_UP,
            Action.MOVE_DOWN,
            input,
        )

    def test_a_cardinal_direction_has_length_one(self):
        actions = movement_map()
        input = SpyInput()
        input.press(Key.D)

        direction = self._vector(actions, input)

        assert direction.x == 1.0
        assert direction.y == 0.0

    def test_up_is_negative_y(self):
        # Y cresce para baixo, como na tela.
        actions = movement_map()
        input = SpyInput()
        input.press(Key.W)

        assert self._vector(actions, input).y == -1.0

    def test_the_diagonal_is_normalized(self):
        # O erro que este metodo existe para apagar: sem normalizar, a
        # diagonal anda 41% mais rapido que a reta.
        actions = movement_map()
        input = SpyInput()
        input.press(Key.D)
        input.press(Key.S)

        direction = self._vector(actions, input)

        assert direction.magnitude() == pytest.approx(1.0)
        assert direction.x == pytest.approx(direction.y)

    def test_nothing_pressed_is_the_zero_vector(self):
        actions = movement_map()

        direction = self._vector(actions, SpyInput())

        assert direction.magnitude() == 0.0

    def test_opposite_directions_cancel_to_zero(self):
        actions = movement_map()
        input = SpyInput()
        input.press(Key.A)
        input.press(Key.D)
        input.press(Key.W)
        input.press(Key.S)

        assert self._vector(actions, SpyInput()).magnitude() == 0.0
        assert self._vector(actions, input).magnitude() == 0.0

    def test_mixed_bindings_of_the_same_action_agree(self):
        actions = movement_map()
        arrows = SpyInput()
        arrows.press(Key.RIGHT)
        arrows.press(Key.DOWN)
        wasd = SpyInput()
        wasd.press(Key.D)
        wasd.press(Key.S)

        assert self._vector(actions, arrows) == self._vector(actions, wasd)


class TestActionsInTheTree:
    """O mapa fala com a porta, entao roda dentro da arvore sem backend."""

    def test_a_node_moves_by_action(self, spy_input):
        actions = movement_map()

        class Walker(Node):
            def on_update(self, dt, input):
                direction = actions.get_vector(
                    Action.MOVE_LEFT,
                    Action.MOVE_RIGHT,
                    Action.MOVE_UP,
                    Action.MOVE_DOWN,
                    input,
                )
                self.transform.position = (
                    self.transform.position + direction * 10.0 * dt
                )

        walker = Walker("Walker")
        spy_input.press(Key.RIGHT)

        walker.update(1.0, spy_input)

        assert walker.transform.position.x == 10.0

    def test_rebinding_changes_the_control_without_touching_the_node(
        self, spy_input
    ):
        # O ganho que justifica o passo: a tecla mudou, e nenhuma linha
        # do no mudou junto.
        actions = ActionMap({Action.JUMP: {Key.SPACE}})
        jumps = []

        class Jumper(Node):
            def on_update(self, dt, input):
                if actions.is_just_pressed(Action.JUMP, input):
                    jumps.append(self.name)

        jumper = Jumper("Jumper")

        spy_input.press(Key.Z)
        jumper.update(0.016, spy_input)
        actions.bind(Action.JUMP, {Key.Z})
        jumper.update(0.016, spy_input)

        assert jumps == ["Jumper"]
