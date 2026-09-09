"""Dubles compartilhados pelos testes.

Nada aqui importa Pyxel: o nucleo da engine fala com portas abstratas,
entao a suite roda headless e sem dependencia grafica.
"""

import pytest

from engine.math.vector2d import Vector2D
from engine.ports.application import Application
from engine.ports.input import Input
from engine.ports.pointer import Pointer
from engine.ports.renderer import Renderer
from engine.scene.node import Node
from engine.scene.scene import Scene


class SpyRenderer(Renderer):
    """Grava as chamadas recebidas em vez de desenhar.

    Guarda os componentes em tuplas planas. Isso ja foi uma DEFESA --
    Vector2D era mutavel, e gravar a referencia deixava um no que
    reaproveitasse o proprio vetor reescrever em silencio as chamadas
    ja anotadas. Com o vetor imutavel a defesa deixou de ser
    necessaria, e a tupla plana permanece por outro motivo: uma
    assercao de igualdade contra `("draw_rect", 10.0, 20.0, ...)` se le
    inteira numa linha.
    """

    def __init__(self):
        self.calls = []

    def clear(self, color=0):
        self.calls.append(("clear", color))

    def draw_rect(self, position, size, color):
        self.calls.append(
            ("draw_rect", position.x, position.y, size.x, size.y, color)
        )

    def draw_sprite(
        self,
        center,
        image,
        region,
        color_key=None,
        rotation=0.0,
        scale=1.0,
    ):
        self.calls.append(
            (
                "draw_sprite",
                center.x,
                center.y,
                image,
                region.x,
                region.y,
                region.width,
                region.height,
                color_key,
                rotation,
                scale,
            )
        )

    def draw_text(self, position, text, color):
        self.calls.append(("draw_text", position.x, position.y, text, color))

    def set_camera(self, offset):
        self.calls.append(("set_camera", offset.x, offset.y))

    def reset_camera(self):
        self.calls.append(("reset_camera",))


class SpyInput(Input):
    """Teclado roteirizado pelo teste.

    Cada conjunto guarda as teclas em um dos tres estados. Estados
    separados de proposito: e o que permite escrever "a tecla esta
    baixa mas NAO desceu neste frame", que e o caso em que um pulo mal
    escrito dispara todo frame.
    """

    def __init__(self, pressed=(), just_pressed=(), just_released=()):
        self.pressed = set(pressed)
        self.just_pressed = set(just_pressed)
        self.just_released = set(just_released)

    def is_pressed(self, key):
        return key in self.pressed

    def is_just_pressed(self, key):
        return key in self.just_pressed

    def is_just_released(self, key):
        return key in self.just_released

    def press(self, key):
        """Simula o frame em que a tecla desce."""
        self.pressed.add(key)
        self.just_pressed.add(key)
        self.just_released.discard(key)

    def hold(self, key):
        """Simula um frame seguinte com a tecla ainda baixa."""
        self.pressed.add(key)
        self.just_pressed.discard(key)
        self.just_released.discard(key)

    def release(self, key):
        """Simula o frame em que a tecla sobe."""
        self.pressed.discard(key)
        self.just_pressed.discard(key)
        self.just_released.add(key)


class SpyPointer(Pointer):
    """Cursor roteirizado pelo teste.

    Guarda um Vector2D e devolve a mesma instancia, sem copia: o vetor
    e imutavel, entao nao ha o que defender -- o teste que guardar a
    referencia devolvida continua vendo o valor que leu.

    `move_to` existe para que o teste escreva o movimento do cursor com
    o mesmo vocabulario de frame que o SpyInput usa para as teclas, em
    vez de reatribuir o campo na mao.
    """

    def __init__(self, position=None):
        self.position = position if position is not None else Vector2D()

    def get_position(self):
        return self.position

    def move_to(self, x, y):
        """Simula o frame em que o cursor apareceu em outro lugar."""
        self.position = Vector2D(x, y)


class SpyApplication(Application):
    """Backend de mentira que roda um numero fixo de frames.

    O quit() interrompe o laco de verdade, como o pyxel.quit() faz --
    um duble que so anotasse a chamada deixaria passar justamente o
    bug de "parou a engine mas a janela continuou girando".
    """

    def __init__(self, frames=1):
        self.frames = frames
        self.config = None
        self.calls = []
        self.frames_run = 0
        self._running = False

    def initialize(self, config):
        self.config = config
        self.calls.append("initialize")

    def run(self, update, render):
        self.calls.append("run")
        self._running = True

        for _ in range(self.frames):
            if not self._running:
                break

            update()
            render()
            self.frames_run += 1

    def quit(self):
        self.calls.append("quit")
        self._running = False


class SpyNode(Node):
    """Anota em uma lista compartilhada tudo que recebe.

    A lista e compartilhada entre os nos da arvore de proposito: e o
    que permite afirmar a ORDEM em que o traversal visitou cada um,
    nao so que visitou.
    """

    def __init__(self, name=None, log=None):
        super().__init__(name)
        self.log = log if log is not None else []

    def on_enter(self):
        self.log.append(("enter", self.name))

    def on_exit(self):
        self.log.append(("exit", self.name))

    def on_update(self, input):
        self.log.append(("update", self.name))

    def on_render(self, renderer):
        self.log.append(("render", self.name))


class SpyScene(Scene):
    """O equivalente do SpyNode na raiz da arvore.

    Nao herda de SpyNode de proposito: Scene.__init__ so aceita `name`,
    entao a heranca multipla engoliria o `log` em silencio.
    """

    def __init__(self, name=None, log=None):
        super().__init__(name)
        self.log = log if log is not None else []

    def on_enter(self):
        self.log.append(("enter", self.name))

    def on_exit(self):
        self.log.append(("exit", self.name))

    def on_update(self, input):
        self.log.append(("update", self.name))

    def on_render(self, renderer):
        self.log.append(("render", self.name))


@pytest.fixture
def renderer():
    return SpyRenderer()


@pytest.fixture
def spy_input():
    # NAO se chama `input`: uma fixture com esse nome, esquecida na
    # assinatura do teste, resolveria em silencio para a funcao
    # embutida `input` e seria passada como se fosse a porta. Com
    # `spy_input` o esquecimento vira NameError na hora.
    return SpyInput()


@pytest.fixture
def pointer():
    return SpyPointer()


@pytest.fixture
def log():
    return []
