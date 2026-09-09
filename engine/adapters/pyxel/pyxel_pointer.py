import pyxel

from engine.math.vector2d import Vector2D
from engine.ports.pointer import Pointer


class PyxelPointer(Pointer):
    # Sem estado proprio, pelo mesmo motivo do PyxelInput: `mouse_x` e
    # `mouse_y` ja sao o valor do frame corrente, e guardar uma copia
    # aqui so criaria a chance de ela discordar da verdade.

    def get_position(self) -> Vector2D:
        # int -> float na fronteira. O Pyxel conta o cursor em pixels
        # inteiros e a engine fala em float em todo lugar; converter
        # aqui evita que a promocao aconteca sozinha no meio da
        # primeira conta do jogo, que e onde ninguem esta olhando.
        return Vector2D(float(pyxel.mouse_x), float(pyxel.mouse_y))
