"""Body: um VisualNode que colide, e nada alem disso."""

from engine.math.anchor import Anchor
from engine.math.rect import Rect
from engine.math.vector2d import Vector2D
from engine.scene.body import Body
from engine.scene.node import Node
from engine.scene.visual_node import VisualNode


class TestWhatABodyIs:
    def test_a_body_is_a_visual_node(self):
        # E de onde vem `size`, `anchor` e `get_world_bounds()`: tudo
        # que a colisao precisa ja estava la, faltava o nome.
        assert isinstance(Body("B"), VisualNode)

    def test_a_visual_node_is_not_a_body(self):
        # A distincao que o tipo compra: o satelite da demo tem caixa e
        # nao deve esbarrar em nada. Se um dia Body virar alias de
        # VisualNode, este teste cai e a decisao volta a mesa.
        assert not isinstance(VisualNode("V"), Body)

    def test_it_takes_the_same_arguments_as_a_visual_node(self):
        body = Body("B", size=Vector2D(8.0, 16.0), anchor=Anchor.BOTTOM_CENTER)

        assert body.name == "B"
        assert body.size == Vector2D(8.0, 16.0)
        assert body.anchor == Anchor.BOTTOM_CENTER

    def test_it_adds_no_state_of_its_own(self):
        # A caixa de colisao E a caixa de desenho. Um segundo `size`
        # seria algo que todo no manteria sincronizado na mao.
        assert set(vars(Body("B"))) == set(vars(VisualNode("V")))


class TestTheCollisionBox:
    def test_the_box_is_the_world_bounds(self):
        parent = Node("P")
        parent.transform.position = Vector2D(100.0, 50.0)

        body = Body("B", size=Vector2D(8.0, 8.0))
        body.transform.position = Vector2D(10.0, 10.0)
        parent.add_child(body)

        assert body.get_world_bounds() == Rect(106.0, 56.0, 8.0, 8.0)

    def test_the_anchor_moves_the_box_not_the_origin(self):
        body = Body("B", size=Vector2D(8.0, 8.0), anchor=Anchor.TOP_LEFT)
        body.transform.position = Vector2D(16.0, 16.0)

        assert body.get_world_bounds() == Rect(16.0, 16.0, 8.0, 8.0)
