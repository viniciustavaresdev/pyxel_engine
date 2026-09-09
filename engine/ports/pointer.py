from abc import ABC, abstractmethod

from engine.math.vector2d import Vector2D


class Pointer(ABC):
    """Onde o cursor esta no frame atual, em coordenadas de TELA.

    Porta propria, e nao um quarto metodo em `Input`, porque a pergunta
    e de outra natureza. Uma tecla responde tres perguntas discretas --
    baixa, desceu agora, subiu agora -- e nao tem analogo continuo;
    um cursor responde uma so, e ela e uma POSICAO. Junta-las daria uma
    porta com dois vocabularios, e obrigaria todo duble de teclado a
    inventar uma posicao que o teste dele nao usa.

    Os BOTOES do mouse fizeram o caminho oposto e entraram no `Key`:
    ali a pergunta e exatamente a mesma que uma tecla ja responde, e
    e por isso que `ActionMap` passa a amarrar `{Key.MOUSE_LEFT, Key.Z}`
    a uma mesma acao sem uma linha nova. Um `MouseButton` separado
    obrigaria o mapa a ser generico em duas dimensoes para nao ganhar
    nada.

    TELA, e nao mundo, e isso e contrato: o adaptador nao conhece
    camera nenhuma. Quem sabe converter e a `Camera`, porque o
    deslocamento e dela -- e na camada `ui` a conversao nao deve nem
    ser chamada, porque ali tela ja E mundo.
    """

    @abstractmethod
    def get_position(self) -> Vector2D:
        """A posicao do cursor, em coordenadas de tela."""
