"""Contrato da porta Renderer, exercido pelo SpyRenderer.

O que se verifica aqui e o formato da fronteira: que a porta aceita
Vector2D e Rect, que o duble desmonta em valores, e que nada do lado da
engine precisa conhecer escalares soltos. O desenho em si e do
adaptador, e esta em tests/infrastructure/.
"""

from engine.math.rect import Rect
from engine.math.vector2d import Vector2D
from engine.ports.renderer import Renderer
from engine.scene.node import Node
from tests.conftest import SpyRenderer


class TestVectorSignatures:
    def test_draw_rect_takes_position_and_size(self, renderer):
        renderer.draw_rect(Vector2D(10.0, 20.0), Vector2D(4.0, 8.0), 11)

        assert renderer.calls == [("draw_rect", 10.0, 20.0, 4.0, 8.0, 11)]

    def test_draw_text_takes_a_position(self, renderer):
        renderer.draw_text(Vector2D(4.0, 4.0), "HP", 7)

        assert renderer.calls == [("draw_text", 4.0, 4.0, "HP", 7)]

    def test_set_camera_takes_an_offset(self, renderer):
        renderer.set_camera(Vector2D(-30.0, 40.0))

        assert renderer.calls == [("set_camera", -30.0, 40.0)]

    def test_draw_sprite_takes_a_center_and_a_region(self, renderer):
        # `center`, nao canto: e em torno deste ponto que o sprite gira.
        renderer.draw_sprite(
            Vector2D(64.0, 32.0), 0, Rect(8.0, 16.0, 8.0, 8.0)
        )

        assert renderer.calls == [
            (
                "draw_sprite",
                64.0,
                32.0,
                0,
                8.0,
                16.0,
                8.0,
                8.0,
                None,
                0.0,
                1.0,
            )
        ]

    def test_draw_sprite_defaults_to_opaque_unrotated_unscaled(self, renderer):
        renderer.draw_sprite(Vector2D(), 0, Rect(0.0, 0.0, 8.0, 8.0))

        color_key, rotation, scale = renderer.calls[0][-3:]

        assert (color_key, rotation, scale) == (None, 0.0, 1.0)

    def test_draw_sprite_carries_the_optional_arguments(self, renderer):
        renderer.draw_sprite(
            Vector2D(),
            2,
            Rect(0.0, 0.0, 8.0, 8.0),
            color_key=0,
            rotation=1.57,
            scale=2.0,
        )

        assert renderer.calls[0][-3:] == (0, 1.57, 2.0)


class TestTheSpyRecordsEachCallSeparately:
    def test_reusing_a_vector_across_calls_is_safe(self):
        # Este teste ja existiu por outro motivo: enquanto Vector2D era
        # mutavel, um no que reaproveitasse o proprio vetor de posicao
        # reescrevia em silencio as chamadas ja anotadas, e o duble
        # precisava desmontar em componentes para se defender.
        #
        # Com valor imutavel a defesa virou desnecessaria. O que ainda
        # merece um teste e o oposto: que reaproveitar o mesmo vetor
        # nao confunde uma chamada com a outra.
        renderer = SpyRenderer()
        size = Vector2D(2.0, 2.0)

        renderer.draw_rect(Vector2D(1.0, 1.0), size, 7)
        renderer.draw_rect(Vector2D(99.0, 1.0), size, 7)

        assert renderer.calls == [
            ("draw_rect", 1.0, 1.0, 2.0, 2.0, 7),
            ("draw_rect", 99.0, 1.0, 2.0, 2.0, 7),
        ]


class TestWorldPositionFlowsStraightIntoTheRenderer:
    def test_a_node_draws_without_unpacking_coordinates(self, renderer):
        # O ganho da mudanca: nenhum `.x, .y` no codigo de jogo.
        class Blob(Node):
            def on_render(self, renderer):
                renderer.draw_rect(
                    self.get_world_position(), Vector2D(8.0, 8.0), 11
                )

        parent = Node("Parent")
        parent.transform.position = Vector2D(100.0, 50.0)
        blob = Blob("Blob")
        blob.transform.position = Vector2D(10.0, 5.0)
        parent.add_child(blob)

        parent.render(renderer)

        assert renderer.calls == [("draw_rect", 110.0, 55.0, 8.0, 8.0, 11)]


class TestPortContract:
    def test_spy_renderer_satisfies_the_port(self):
        assert isinstance(SpyRenderer(), Renderer)

    def test_the_port_has_no_unimplemented_methods(self):
        assert Renderer.__abstractmethods__ - set(dir(SpyRenderer())) == set()
