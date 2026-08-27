from engine import (
    Anchor,
    ApplicationConfig,
    Camera,
    Clock,
    Engine,
    Game,
    Input,
    Key,
    Node,
    Renderer,
    Scene,
    SceneManager,
    Vector2D,
    VisualNode,
)

# Os adaptadores vem pelo caminho completo, e nao pelo `from engine`:
# sao a unica parte deste arquivo que amarra o jogo ao Pyxel, e a
# forma do import deixa isso a vista.
from engine.adapters.pyxel.pyxel_application import PyxelApplication
from engine.adapters.pyxel.pyxel_input import PyxelInput
from engine.adapters.pyxel.pyxel_renderer import PyxelRenderer
from engine.adapters.stdlib.performance_time_provider import (
    PerformanceTimeProvider,
)

SCREEN_WIDTH = 160
SCREEN_HEIGHT = 120

# De proposito muito maior que a tela: e o que torna a camera visivel.
WORLD_WIDTH = 480
WORLD_HEIGHT = 360

PLAYER_SIZE = 8.0
PLAYER_SPEED = 70.0
SPIN_SPEED = 3.0


class Player(VisualNode):
    # Le o teclado pela porta Input. Nenhum `import pyxel` aqui: o no
    # nao sabe em que backend esta rodando.
    #
    # VisualNode e nao Node: a partir daqui a posicao do jogador e o
    # CENTRO dele, porque o anchor default e Anchor.CENTER. E o que faz
    # o satelite orbitar o meio do quadrado e a camera enquadrar o meio
    # do quadrado, sem uma linha de correcao em nenhum dos dois.

    def __init__(self, name: str | None = None) -> None:
        super().__init__(name, size=Vector2D(PLAYER_SIZE, PLAYER_SIZE))

        self.color = 11

    def on_update(self, dt: float, input: Input) -> None:
        # Acumula em escalares e monta o vetor uma vez so. Vector2D e
        # imutavel, entao `direction.x -= 1` nao existe -- e o estilo
        # que sobra e mais direto do que o que ele substituiu.
        horizontal = 0.0
        vertical = 0.0

        if input.is_pressed(Key.LEFT) or input.is_pressed(Key.A):
            horizontal -= 1.0
        if input.is_pressed(Key.RIGHT) or input.is_pressed(Key.D):
            horizontal += 1.0
        if input.is_pressed(Key.UP) or input.is_pressed(Key.W):
            vertical -= 1.0
        if input.is_pressed(Key.DOWN) or input.is_pressed(Key.S):
            vertical += 1.0

        direction = Vector2D(horizontal, vertical)

        # normalized() evita andar mais rapido na diagonal.
        position = (
            self.transform.position
            + direction.normalized() * PLAYER_SPEED * dt
        )

        # Os limites recuam meia caixa de cada lado: com a origem no
        # centro, prender a posicao em [0, mundo] deixaria metade do
        # jogador para fora da borda.
        half = PLAYER_SIZE / 2.0

        self.transform.position = Vector2D(
            min(max(position.x, half), WORLD_WIDTH - half),
            min(max(position.y, half), WORLD_HEIGHT - half),
        )

        if input.is_pressed(Key.SPACE):
            self.transform.rotation += SPIN_SPEED * dt
        else:
            self.transform.rotation = 0.0

    def on_render(self, renderer: Renderer) -> None:
        # get_world_bounds, e nao get_world_position: draw_rect fala em
        # canto porque nao sabe girar, e a conversao a partir do anchor
        # e do VisualNode. Uma chamada so em vez de top_left + size:
        # sao duas subidas da hierarquia inteira contra uma.
        bounds = self.get_world_bounds()

        renderer.draw_rect(bounds.position, bounds.size, self.color)


class Satellite(VisualNode):
    # Sem uma linha sobre movimento: segue e orbita o pai apenas por
    # estar pendurado nele. O raio da orbita e a distancia local ate a
    # origem do pai -- que agora e o centro dele.

    def __init__(self, name: str | None = None) -> None:
        super().__init__(name, size=Vector2D(3.0, 3.0))

        self.transform.position = Vector2D(PLAYER_SIZE/2, 0)
        self.color = 8

    def on_update(self, dt: float, input: Input) -> None:
        self.transform.rotation += SPIN_SPEED * dt

    def on_render(self, renderer: Renderer) -> None:
        bounds = self.get_world_bounds()

        renderer.draw_rect(bounds.position, bounds.size, self.color)


class Landmark(VisualNode):
    # Parado no mundo. E o referencial que revela que quem se move e a
    # camera, e nao o cenario.

    def __init__(
        self, name: str | None = None, position: Vector2D | None = None
    ) -> None:
        # Anchor.TOP_LEFT de proposito: um marco de grade e util
        # justamente por comecar exatamente na coordenada que nomeia.
        # Serve para mostrar que o anchor e uma escolha por no, e nao
        # uma regra global da engine.
        super().__init__(name, size=Vector2D(6.0, 6.0), anchor=Anchor.TOP_LEFT)

        if position is not None:
            self.transform.position = position

        self.color = 3

    def on_render(self, renderer: Renderer) -> None:
        bounds = self.get_world_bounds()

        renderer.draw_rect(bounds.position, bounds.size, self.color)


class Hud(Node):
    # Desenha em coordenadas de TELA: reset_camera desfaz o
    # enquadramento aplicado pela cena, entao o texto nao rola junto
    # com o mundo.
    #
    # Depende de ser o ultimo filho a desenhar. A solucao propria e uma
    # camada de render dedicada -- que ainda nao existe, junto com o
    # z-index.

    def __init__(self, name: str | None = None, player: Node | None = None):
        super().__init__(name)

        self.player = player

    def on_render(self, renderer: Renderer) -> None:
        renderer.reset_camera()

        renderer.draw_text(Vector2D(4.0, 4.0), "WASD/SETAS mover", 7)
        renderer.draw_text(Vector2D(4.0, 12.0), "ESPACO girar", 7)

        if self.player is not None:
            position = self.player.get_world_position()
            renderer.draw_text(
                Vector2D(4.0, SCREEN_HEIGHT - 10.0),
                f"x{int(position.x)} y{int(position.y)}",
                7,
            )


class DemoScene(Scene):

    def __init__(self, name: str | None = None) -> None:
        super().__init__(name)

        player = Player("Player")
        player.transform.position = Vector2D(
           0,0
        )

        satellite = Satellite("Satellite")
        lua = Satellite("lua")

        #satellite.add_child(lua)
        player.add_child(satellite)

        # Pendurada no jogador: a camera o segue pela propria transform
        # hierarquica, sem codigo de follow.
        camera = Camera(
            "Camera",
            viewport_width=SCREEN_WIDTH,
            viewport_height=SCREEN_HEIGHT,
        )
        player.add_child(camera)
        self.camera = camera

        for x in range(0, WORLD_WIDTH, 60):
            for y in range(0, WORLD_HEIGHT, 60):
                self.add_child(
                    Landmark(f"Landmark{x}_{y}", Vector2D(float(x), float(y)))
                )

        self.add_child(player)
        self.add_child(Hud("Hud", player))


def main() -> None:

    application = PyxelApplication()

    time_provider = PerformanceTimeProvider()

    clock = Clock(time_provider)

    scene_manager = SceneManager()

    renderer = PyxelRenderer()

    input = PyxelInput()

    engine = Engine(
        clock=clock,
        scene_manager=scene_manager,
        renderer=renderer,
        input=input,
    )

    config = ApplicationConfig(
        width=SCREEN_WIDTH,
        height=SCREEN_HEIGHT,
        title="My Game",
        fps=60,
    )

    game = Game(
        application=application,
        engine=engine,
        config=config,
        # O Game carrega a cena depois do initialize, para que o
        # on_enter encontre o backend ja de pe.
        initial_scene=DemoScene("Demo"),
    )

    game.run()


if __name__ == "__main__":
    main()
