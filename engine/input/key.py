from enum import Enum, auto


class Key(Enum):
    """Teclas que a engine reconhece, independentes do backend.

    Enum proprio em vez de repassar os `pyxel.KEY_*`: e o que mantem o
    codigo de jogo sem `import pyxel`. Trocar de backend passa a ser
    escrever outro adaptador, nao caçar constantes espalhadas pelas
    cenas.

    Acrescentar uma tecla e duas linhas: uma entrada aqui e uma no
    mapa do adaptador. O adaptador tem teste que falha se a segunda
    for esquecida.
    """

    # Direcionais
    UP = auto()
    DOWN = auto()
    LEFT = auto()
    RIGHT = auto()

    # WASD
    W = auto()
    A = auto()
    S = auto()
    D = auto()

    # Botoes de acao
    Z = auto()
    X = auto()
    C = auto()

    SPACE = auto()
    ENTER = auto()
    ESCAPE = auto()
    SHIFT = auto()
