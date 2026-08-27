import pyxel

from engine.input.key import Key
from engine.ports.input import Input

# Unico ponto do projeto que sabe como uma Key da engine se chama no
# Pyxel. Se uma Key nova nao aparecer aqui, o teste de completude do
# mapa falha antes de virar KeyError em pleno jogo.
_PYXEL_KEYS: dict[Key, int] = {
    Key.UP: pyxel.KEY_UP,
    Key.DOWN: pyxel.KEY_DOWN,
    Key.LEFT: pyxel.KEY_LEFT,
    Key.RIGHT: pyxel.KEY_RIGHT,
    Key.W: pyxel.KEY_W,
    Key.A: pyxel.KEY_A,
    Key.S: pyxel.KEY_S,
    Key.D: pyxel.KEY_D,
    Key.Z: pyxel.KEY_Z,
    Key.X: pyxel.KEY_X,
    Key.C: pyxel.KEY_C,
    Key.SPACE: pyxel.KEY_SPACE,
    Key.ENTER: pyxel.KEY_RETURN,
    Key.ESCAPE: pyxel.KEY_ESCAPE,
    Key.SHIFT: pyxel.KEY_SHIFT,
}


class PyxelInput(Input):
    # Sem estado proprio: o Pyxel ja distingue baixa, desceu-agora e
    # subiu-agora. Guardar uma copia aqui so criaria a chance de ela
    # discordar da verdade.

    def is_pressed(self, key: Key) -> bool:
        return pyxel.btn(_PYXEL_KEYS[key])

    def is_just_pressed(self, key: Key) -> bool:
        return pyxel.btnp(_PYXEL_KEYS[key])

    def is_just_released(self, key: Key) -> bool:
        return pyxel.btnr(_PYXEL_KEYS[key])
