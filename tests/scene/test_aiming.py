"""O caminho da mira, ponta a ponta e sem janela.

As tres pecas da semana 1 encontradas de uma vez: o ponteiro responde
em TELA, a camera converte para MUNDO, e o no escreve o angulo na
propria rotacao. Cada peca tem teste proprio; o que so aparece aqui e
a COMPOSICAO -- um erro de sinal em qualquer uma delas sobrevive aos
testes unitarios e morre neste arquivo.

O arranjo e o mesmo da demo: a camera pendurada no jogador, em (0, 0)
local. Nao e coincidencia -- e o unico arranjo em que apontar nao move
o enquadramento, e e por isso que ele e o testado.
"""

import math

import pytest

from engine.math.vector2d import Vector2D
from engine.scene.camera import Camera
from engine.scene.scene import Scene
from engine.scene.visual_node import VisualNode
from tests.conftest import SpyPointer

SCREEN_WIDTH = 160.0
SCREEN_HEIGHT = 120.0

SCREEN_CENTER = Vector2D(SCREEN_WIDTH / 2.0, SCREEN_HEIGHT / 2.0)

# Constante de modulo, e nao `Vector2D()` na assinatura do build: o
# vetor e congelado, entao compartilhar a instancia e inofensivo -- e
# o mesmo motivo pelo qual o Transform trocou os default_factory por
# defaults literais.
ORIGIN = Vector2D(0.0, 0.0)


class Aimer(VisualNode):
    """O `Player.on_update` da demo, reduzido a mira.

    Sem movimento e sem tiro: o que se verifica aqui e o angulo, e um
    nó que também andasse misturaria duas causas no mesmo assert.
    """

    def __init__(self, name, pointer, camera):
        super().__init__(name, size=Vector2D(8.0, 8.0))

        self.pointer = pointer
        self.camera = camera
        self.aim_target = Vector2D()

    def on_update(self, input):
        self.aim_target = self.camera.screen_to_world(
            self.pointer.get_position()
        )

        to_target = self.aim_target - self.get_world_position()

        if to_target.magnitude() == 0.0:
            return

        self.transform.rotation = math.atan2(to_target.y, to_target.x)


def build(world_position=ORIGIN):
    scene = Scene("Level")
    pointer = SpyPointer()

    camera = Camera(
        "Camera",
        viewport_width=SCREEN_WIDTH,
        viewport_height=SCREEN_HEIGHT,
    )

    aimer = Aimer("Aimer", pointer, camera)
    aimer.transform.position = world_position

    # A camera em (0, 0) LOCAL, como na demo.
    aimer.add_child(camera)
    scene.world.add_child(aimer)
    scene.camera = camera

    return scene, aimer, pointer


class TestTheCursorDecidesTheAngle:
    """Y cresce para BAIXO, entao o angulo positivo desce na tela.

    E a convencao de todo engine 2D com origem no topo-esquerdo, e a
    mesma que `Vector2D.rotated` usa -- a frente do no e o eixo +X
    local, e `atan2(dy, dx)` e exatamente o angulo que leva +X ate o
    alvo.
    """

    CARDINALS = [
        # (deslocamento do cursor na tela, angulo esperado)
        (Vector2D(40.0, 0.0), 0.0),
        (Vector2D(0.0, 40.0), math.pi / 2.0),
        (Vector2D(-40.0, 0.0), math.pi),
        (Vector2D(0.0, -40.0), -math.pi / 2.0),
        (Vector2D(40.0, 40.0), math.pi / 4.0),
        (Vector2D(-40.0, -40.0), -3.0 * math.pi / 4.0),
    ]

    @pytest.mark.parametrize("offset, expected", CARDINALS)
    def test_it_points_at_the_cursor(self, offset, expected, spy_input):
        scene, aimer, pointer = build()
        cursor = SCREEN_CENTER + offset

        pointer.move_to(cursor.x, cursor.y)
        scene.update(spy_input)

        assert aimer.transform.rotation == pytest.approx(expected)

    def test_the_forward_axis_really_points_there(self, spy_input):
        # O angulo em si e so um numero. O que ele promete e que o eixo
        # +X local do no passa a apontar para o alvo -- e e isso que faz
        # um filho em (10, 0) virar indicador de mira. Perguntado pelo
        # mesmo `rotated` que a engine usa para compor transforms.
        scene, aimer, pointer = build(Vector2D(200.0, 150.0))

        cursor = SCREEN_CENTER + Vector2D(30.0, 40.0)
        pointer.move_to(cursor.x, cursor.y)
        scene.update(spy_input)

        forward = Vector2D(1.0, 0.0).rotated(aimer.transform.rotation)
        to_target = (
            aimer.aim_target - aimer.get_world_position()
        ).normalized()

        assert forward.x == pytest.approx(to_target.x)
        assert forward.y == pytest.approx(to_target.y)


class TestItHoldsAnywhereInTheWorld:
    """O criterio que o plano nomeia: girar certo PERTO DA BORDA.

    E onde uma conversao tela -> mundo errada aparece. Com o jogador na
    origem, um `screen_to_world` que esquecesse o offset da camera
    erraria por meia tela e poderia ainda parecer certo; longe da
    origem, nao ha como o erro se esconder.
    """

    POSITIONS = [
        Vector2D(0.0, 0.0),
        Vector2D(4.0, 4.0),
        Vector2D(240.0, 180.0),
        Vector2D(476.0, 356.0),
        Vector2D(-100.0, -100.0),
    ]

    @pytest.mark.parametrize("world_position", POSITIONS)
    def test_the_angle_does_not_depend_on_where_the_player_is(
        self, world_position, spy_input
    ):
        scene, aimer, pointer = build(world_position)
        cursor = SCREEN_CENTER + Vector2D(40.0, 0.0)

        pointer.move_to(cursor.x, cursor.y)
        scene.update(spy_input)

        assert aimer.transform.rotation == pytest.approx(0.0)

    @pytest.mark.parametrize("world_position", POSITIONS)
    def test_the_screen_center_is_always_the_player(
        self, world_position, spy_input
    ):
        # A ancora de tudo: com a camera centrada no jogador, o cursor
        # no meio da tela cai exatamente sobre ele.
        scene, aimer, pointer = build(world_position)

        pointer.move_to(SCREEN_CENTER.x, SCREEN_CENTER.y)
        scene.update(spy_input)

        assert aimer.aim_target == world_position


class TestTheCursorOverTheOriginKeepsTheLastDirection:
    """atan2(0, 0) devolve 0.0 -- um tranco para a direita.

    Sem a guarda, passar o mouse por cima do proprio jogador faria ele
    virar para leste. E o tipo de defeito que nao quebra nada e incomoda
    em todo frame.
    """

    def test_it_does_not_snap_east(self, spy_input):
        scene, aimer, pointer = build()

        cursor = SCREEN_CENTER + Vector2D(0.0, -40.0)
        pointer.move_to(cursor.x, cursor.y)
        scene.update(spy_input)

        facing_up = aimer.transform.rotation

        pointer.move_to(SCREEN_CENTER.x, SCREEN_CENTER.y)
        scene.update(spy_input)

        assert aimer.transform.rotation == facing_up

    def test_without_the_guard_it_would_have_snapped(self):
        # O que a guarda evita, dito explicitamente: se a conta rodasse
        # com o vetor zero, o angulo seria zero.
        assert math.atan2(0.0, 0.0) == 0.0


class TestAimingDoesNotMoveTheFraming:
    """Por que a camera mora em (0, 0) local.

    Deslocada, ela seria varrida pelo mundo a cada mexida do mouse: o
    enquadramento mudaria, o alvo convertido mudaria com ele, e a mira
    perseguiria o proprio rabo. Este teste e o que impede alguem de
    "melhorar" a demo olhando adiante do jogador sem notar o
    acoplamento.
    """

    def test_a_centered_camera_is_unmoved_by_rotation(self, spy_input):
        scene, aimer, pointer = build(Vector2D(200.0, 150.0))
        before = aimer.camera.get_view_offset()

        cursor = SCREEN_CENTER + Vector2D(40.0, 40.0)
        pointer.move_to(cursor.x, cursor.y)
        scene.update(spy_input)

        assert aimer.camera.get_view_offset() == before

    def test_the_aim_is_stable_across_frames(self, spy_input):
        # O cursor parado tem de dar o mesmo alvo em todo frame. Se o
        # enquadramento se mexesse por causa da rotacao, este assert
        # falharia no segundo frame.
        scene, aimer, pointer = build(Vector2D(200.0, 150.0))
        cursor = SCREEN_CENTER + Vector2D(37.0, -19.0)
        pointer.move_to(cursor.x, cursor.y)

        seen = []

        for _ in range(5):
            scene.update(spy_input)
            seen.append((aimer.aim_target, aimer.transform.rotation))

        assert len(set(seen)) == 1

    def test_an_offset_camera_would_drift(self, spy_input):
        # O contraponto que mantem o teste acima honesto: com a camera
        # deslocada, girar MOVE o enquadramento de verdade. Nao e um bug
        # da engine -- e por isso que a demo a mantem centrada.
        scene, aimer, pointer = build(Vector2D(200.0, 150.0))
        aimer.camera.transform.position = Vector2D(20.0, 0.0)
        before = aimer.camera.get_view_offset()

        cursor = SCREEN_CENTER + Vector2D(0.0, 40.0)
        pointer.move_to(cursor.x, cursor.y)
        scene.update(spy_input)

        assert aimer.camera.get_view_offset() != before
