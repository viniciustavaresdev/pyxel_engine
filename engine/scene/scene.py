from __future__ import annotations

from engine.ports.renderer import Renderer
from engine.scene.camera import Camera
from engine.scene.node import Node


class Scene(Node):
    """A raiz de uma tela de jogo, e quem decide o ESPACO do desenho.

    Duas subarvores, criadas aqui e penduradas na cena como filhas
    comuns: `world` desenha enquadrada pela camera, `ui` desenha em
    coordenadas de tela. Quem decide isso e a cena, no `render` -- e nao
    um `reset_camera()` escondido no `on_render` de algum no, que
    dependia de aquele no ser o ultimo filho e alterava estado global do
    renderer no meio da travessia.

    Elas sao Nodes comuns, e nao um mecanismo paralelo: entram no
    `update`, no `enter`/`exit` e na fila de remocao pelos mesmos
    caminhos de sempre, sem uma linha nova. A camada e um conceito de
    ORDEM e ESPACO de desenho, so isso.

    O que `world` ganha por existir, mesmo com filhos diretos da cena ja
    desenhando em espaco de mundo, e poder ser tratado como uma coisa
    so:

        scene.world.active = False      # pausa o jogo; a UI segue viva
        scene.world.visible = False     # tira o mundo, mantem o menu
    """

    def __init__(self, name: str | None = None) -> None:
        super().__init__(name)

        # A camera e da cena, nao da Engine: cada cena enquadra o
        # proprio mundo, e trocar de cena troca o enquadramento junto.
        self._camera: Camera | None = None

        # A ordem importa duas vezes: `world` primeiro porque e a ordem
        # de update, e `ui` por ultimo porque render a trata como
        # excecao explicita -- ela desenha depois de todo mundo.
        self._world = Node("World")
        self._ui = Node("UI")

        self.add_child(self._world)
        self.add_child(self._ui)

    # Layers
    @property
    def world(self) -> Node:
        """A subarvore que desenha enquadrada pela camera.

        So leitura: trocar a camada por outro no deixaria a antiga
        pendurada na cena, ainda desenhando, e o `render` procurando a
        nova. Para esvaziar, `remove_child` nos filhos dela.
        """
        return self._world

    @property
    def ui(self) -> Node:
        """A subarvore que desenha em coordenadas de TELA.

        Desenha depois do mundo inteiro, sempre -- e nao por ser o
        ultimo filho da lista, mas porque o render da cena a trata como
        uma passada separada.
        """
        return self._ui

    @property
    def camera(self) -> Camera | None:
        """A camera ativa -- se ela ainda pertencer a esta arvore.

        A referencia e forte e ninguem a limpa quando a camera sai da
        arvore. Sem esta guarda, uma camera arrancada continuaria
        enquadrando: com `parent` valendo None, get_world_position()
        cai na transform LOCAL dela, e a vista salta para outro canto
        do mundo sem erro nenhum -- falha silenciosa, o pior modo.

        A pergunta e "esta camera esta pendurada em MIM?", e nao
        `is_inside_tree`: a cena precisa poder ser montada e desenhada
        antes de receber o enter(), e nesse intervalo `is_inside_tree`
        ainda e falso para todo mundo.

        Tambem nao e "a raiz da camera sou eu": uma Scene e um Node, e
        cena dentro de cena e o caminho previsto. Ali a raiz seria a
        cena de fora, e a de dentro perderia o proprio enquadramento.
        Ascendencia responde certo nos dois arranjos.
        """
        if self._camera is not None and not self.is_ancestor_of(self._camera):
            return None

        return self._camera

    @camera.setter
    def camera(self, camera: Camera | None) -> None:
        self._camera = camera

    def render(self, renderer: Renderer) -> None:
        """Duas passadas: o mundo enquadrado, a UI em espaco de tela.

        O enquadramento e aplicado aqui, na raiz, e nao num on_render de
        algum no: se dependesse da ordem de visita, bastaria alguem
        reordenar os filhos para metade da cena desenhar com o
        enquadramento errado.
        """
        # Lido uma vez: a property faz a checagem de ascendencia, e
        # entre duas leituras nada garante a mesma resposta.
        camera = self.camera

        if camera is None:
            renderer.reset_camera()
        else:
            renderer.set_camera(camera.get_view_offset())

        if not self.visible:
            return

        self.on_render(renderer)

        # A travessia do Node, menos a camada de UI. Filho direto da
        # cena continua desenhando em espaco de mundo, como sempre
        # desenhou: a UI e a unica excecao, e ela e declarada.
        for child in tuple(self.children):
            if child is not self._ui:
                child.render(renderer)

        self._render_ui(renderer)

    def _render_ui(self, renderer: Renderer) -> None:
        # Camada vazia nao custa chamada nenhuma. E o que mantem uma
        # cena que nao usa UI com exatamente o mesmo trafego de renderer
        # de antes de as camadas existirem -- e o reset_camera aparece
        # no frame por um motivo visivel, nao por cerimonia.
        if not self._ui.visible or not self._ui.children:
            return

        renderer.reset_camera()

        self._ui.render(renderer)
