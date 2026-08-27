from __future__ import annotations

from engine.ports.renderer import Renderer
from engine.scene.camera import Camera
from engine.scene.node import Node


class Scene(Node):

    def __init__(self, name: str | None = None) -> None:
        super().__init__(name)

        # A camera e da cena, nao da Engine: cada cena enquadra o
        # proprio mundo, e trocar de cena troca o enquadramento junto.
        self._camera: Camera | None = None

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
        # Aplicado aqui, na raiz, e nao num on_render de algum no: se
        # dependesse da ordem de visita, bastaria alguem reordenar os
        # filhos para metade da cena desenhar com o enquadramento
        # errado.
        # Lido uma vez: a property faz a checagem de raiz, e entre duas
        # leituras nada garante a mesma resposta.
        camera = self.camera

        if camera is None:
            renderer.reset_camera()
        else:
            renderer.set_camera(camera.get_view_offset())

        super().render(renderer)
