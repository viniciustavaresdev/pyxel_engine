from enum import Enum, auto

from engine import (
    ActionMap,
    Anchor,
    ApplicationConfig,
    Camera,
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

SCREEN_WIDTH = 160
SCREEN_HEIGHT = 120
FPS = 60

# De proposito muito maior que a tela: e o que torna a camera visivel.
WORLD_WIDTH = 480
WORLD_HEIGHT = 360

PLAYER_SIZE = 8.0

# POR FRAME, e nao por segundo: um update e um frame, e a engine nao
# mede tempo. A 60 fps isto da 72 px/s e 3 rad/s -- mas quem governa e
# o numero de frames, entao trocar o FPS aqui em cima muda a velocidade
# do jogo junto.
PLAYER_SPEED = 1.2
SPIN_SPEED = 0.05


class Action(Enum):
    # O vocabulario deste jogo, e nao da engine: "girar" nao e um
    # conceito que uma engine 2D possa enumerar de antemao. O Enum e do
    # jogo, e por ser um Enum um nome errado quebra no mypy, antes de
    # virar um controle que nao responde.
    MOVE_LEFT = auto()
    MOVE_RIGHT = auto()
    MOVE_UP = auto()
    MOVE_DOWN = auto()
    SPIN = auto()


# A lista de teclas mora AQUI, uma vez. Antes ela se repetia em quatro
# linhas do on_update do Player -- e remapear era caçar todas.
DEMO_BINDINGS: ActionMap[Action] = ActionMap(
    {
        Action.MOVE_LEFT: {Key.LEFT, Key.A},
        Action.MOVE_RIGHT: {Key.RIGHT, Key.D},
        Action.MOVE_UP: {Key.UP, Key.W},
        Action.MOVE_DOWN: {Key.DOWN, Key.S},
        Action.SPIN: {Key.SPACE},
    }
)


class Player(VisualNode):
    # Le o teclado pela porta Input. Nenhum `import pyxel` aqui: o no
    # nao sabe em que backend esta rodando.
    #
    # VisualNode e nao Node: a partir daqui a posicao do jogador e o
    # CENTRO dele, porque o anchor default e Anchor.CENTER. E o que faz
    # o satelite orbitar o meio do quadrado e a camera enquadrar o meio
    # do quadrado, sem uma linha de correcao em nenhum dos dois.

    def __init__(
        self,
        name: str | None = None,
        actions: ActionMap[Action] | None = None,
    ) -> None:
        super().__init__(name, size=Vector2D(PLAYER_SIZE, PLAYER_SIZE))

        # O mapa chega pelo construtor, e nao como global: e
        # configuracao do jogo, e um no que a recebe pode ser exercitado
        # com outro mapa sem tocar em nada aqui dentro.
        self.actions = actions if actions is not None else DEMO_BINDINGS

        self.color = 11

    def on_update(self, input: Input) -> None:
        # Uma linha no lugar de oito. O no nomeia intencoes; quais
        # teclas as produzem e assunto do mapa -- e get_vector ja
        # devolve normalizado, entao a diagonal nao anda mais rapido
        # sem que ninguem precise lembrar disso aqui.
        direction = self.actions.get_vector(
            Action.MOVE_LEFT,
            Action.MOVE_RIGHT,
            Action.MOVE_UP,
            Action.MOVE_DOWN,
            input,
        )

        position = self.transform.position + direction * PLAYER_SPEED

        # Os limites recuam meia caixa de cada lado: com a origem no
        # centro, prender a posicao em [0, mundo] deixaria metade do
        # jogador para fora da borda.

        half = PLAYER_SIZE / 2.0

        self.transform.position = Vector2D(
            min(max(position.x, half), WORLD_WIDTH - half),
            min(max(position.y, half), WORLD_HEIGHT - half),
        )

        if self.actions.is_pressed(Action.SPIN, input):
            self.transform.rotation += SPIN_SPEED
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
        super().__init__(name, size=Vector2D(4.0, 4.0))

        self.transform.position = Vector2D(10.0, 0.0)
        self.color = 8

    def on_update(self, input: Input) -> None:
        self.transform.rotation += SPIN_SPEED

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
    # Desenha em coordenadas de TELA -- e nao faz nada para isso. Vive
    # na camada `ui` da cena, e e a cena que sai do enquadramento antes
    # da passada dela.
    #
    # Antes, este no chamava reset_camera() no proprio on_render e
    # dependia de ser o ultimo filho a desenhar: estado global do
    # renderer alterado no meio da travessia, com uma ordem que ninguem
    # declarava em lugar nenhum.

    def __init__(self, name: str | None = None, player: Node | None = None):
        super().__init__(name)

        self.player = player

    def on_render(self, renderer: Renderer) -> None:
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

        player = Player("Player", DEMO_BINDINGS)
        player.transform.position = Vector2D(0.0, 0.0)

        satellite = Satellite("Satellite")

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
                self.world.add_child(
                    Landmark(f"Landmark{x}_{y}", Vector2D(float(x), float(y)))
                )

        # Cada um na camada que diz em que espaco desenha. A ordem em
        # que aparecem aqui deixou de importar: a UI desenha depois do
        # mundo porque e a cena que decide isso, e nao a posicao na
        # lista de filhos.
        self.world.add_child(player)
        self.ui.add_child(Hud("Hud", player))


def main() -> None:

    application = PyxelApplication()

    scene_manager = SceneManager()

    renderer = PyxelRenderer()

    input = PyxelInput()

    engine = Engine(
        scene_manager=scene_manager,
        renderer=renderer,
        input=input,
    )

    config = ApplicationConfig(
        width=SCREEN_WIDTH,
        height=SCREEN_HEIGHT,
        title="My Game",
        fps=FPS,
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
