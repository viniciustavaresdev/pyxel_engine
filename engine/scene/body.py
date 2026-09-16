from __future__ import annotations

from engine.scene.visual_node import VisualNode


class Body(VisualNode):
    """Um no que COLIDE.

    Nao acrescenta campo nenhum ao VisualNode, e isso e o ponto: colisao
    precisa de `size` e `anchor`, que e exatamente o que o VisualNode ja
    acrescenta ao Node, e `get_world_bounds()` ja entrega a caixa
    resolvendo a transform mundial uma vez so. O que faltava nao era
    dado, era um NOME -- um jeito de dizer que este no participa da
    colisao e aquele nao.

    Nem todo VisualNode e um corpo. O satelite da demo tem tamanho e
    anchor e nao deve esbarrar em parede nenhuma; um decalque de sangue
    tem caixa e e atravessavel por definicao. Tipar `move_and_slide` e
    `bodies_in` em `Body`, e nao em `VisualNode`, e o que faz um no que
    nunca deveria colidir aparecer como erro de mypy em vez de como um
    fantasma solido no meio do andar.

    A caixa de colisao e a caixa de desenho -- uma so, alinhada aos
    eixos. Separar as duas entraria no dia em que um jogo pedisse um
    sprite maior que o corpo dele; ate la, seria um segundo `size` que
    todo no manteria sincronizado na mao.
    """
