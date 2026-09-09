import math
from enum import Enum, auto

from engine import (
    ActionMap,
    Anchor,
    ApplicationConfig,
    Camera,
    Cooldown,
    Engine,
    Game,
    Input,
    Key,
    Node,
    Pointer,
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
from engine.adapters.pyxel.pyxel_pointer import PyxelPointer
from engine.adapters.pyxel.pyxel_renderer import PyxelRenderer

SCREEN_WIDTH = 160
SCREEN_HEIGHT = 120
FPS = 60

# De proposito muito maior que a tela: e o que torna a camera visivel.
WORLD_WIDTH = 480
WORLD_HEIGHT = 360

PLAYER_SIZE = 8.0

# POR FRAME, e nao por segundo: um update e um frame, e a engine nao
# mede tempo. A 60 fps isto da 72 px/s -- mas quem governa e o numero
# de frames, entao trocar o FPS aqui em cima muda a velocidade do jogo
# junto.
PLAYER_SPEED = 1.2

# Em FRAMES, como toda duracao daqui para frente. A 60 fps, 12 frames
# sao 0,2 s -- cinco tiros por segundo.
FIRE_COOLDOWN = 12
FLASH_FRAMES = 3

PLAYER_COLOR = 11
FLASH_COLOR = 7

# Em radianos por frame. E o giro do satelite em torno do PROPRIO
# centro; a orbita dele em volta do jogador vem da transform do pai.
SATELLITE_SPIN = 0.05


class Action(Enum):
    # O vocabulario deste jogo, e nao da engine: "atirar" nao e um
    # conceito que uma engine 2D possa enumerar de antemao. O Enum e do
    # jogo, e por ser um Enum um nome errado quebra no mypy, antes de
    # virar um controle que nao responde.
    MOVE_LEFT = auto()
    MOVE_RIGHT = auto()
    MOVE_UP = auto()
    MOVE_DOWN = auto()
    FIRE = auto()


# A lista de teclas mora AQUI, uma vez. Antes ela se repetia em quatro
# linhas do on_update do Player -- e remapear era caçar todas.
#
# FIRE amarra botao de mouse e tecla no MESMO conjunto, e e o ganho de
# os botoes terem entrado no `Key` em vez de num enum proprio: o mapa
# nao precisou de uma linha nova para entender um mouse.
DEMO_BINDINGS: ActionMap[Action] = ActionMap(
    {
        Action.MOVE_LEFT: {Key.LEFT, Key.A},
        Action.MOVE_RIGHT: {Key.RIGHT, Key.D},
        Action.MOVE_UP: {Key.UP, Key.W},
        Action.MOVE_DOWN: {Key.DOWN, Key.S},
        Action.FIRE: {Key.MOUSE_LEFT, Key.Z},
    }
)


class Player(VisualNode):
    # Le o teclado pela porta Input e o cursor pela porta Pointer.
    # Nenhum `import pyxel` aqui: o no nao sabe em que backend esta
    # rodando, e nem que existe um mouse de verdade do outro lado.
    #
    # VisualNode e nao Node: a partir daqui a posicao do jogador e o
    # CENTRO dele, porque o anchor default e Anchor.CENTER. E o que faz
    # o satelite orbitar o meio do quadrado e a camera enquadrar o meio
    # do quadrado, sem uma linha de correcao em nenhum dos dois.

    def __init__(
        self,
        name: str,
        actions: ActionMap[Action],
        pointer: Pointer,
        camera: Camera,
    ) -> None:
        super().__init__(name, size=Vector2D(PLAYER_SIZE, PLAYER_SIZE))

        # As quatro dependencias chegam pelo construtor, e nenhuma e
        # opcional. Sao configuracao do jogo, nao estado global -- e
        # exigi-las obriga quem monta a cena a dizer de onde vem cada
        # uma, em vez de um default silencioso responder por ele.
        #
        # A camera esta aqui por um motivo so: ela e quem sabe converter
        # tela -> mundo. Nao e para mover nem para enquadrar.
        self.actions = actions
        self.pointer = pointer
        self.camera = camera

        self.color = PLAYER_COLOR

        self.fire_cooldown = Cooldown(FIRE_COOLDOWN)
        self.flash = Cooldown(FLASH_FRAMES)

        # Guardado para o HUD poder desenhar sem precisar da camera.
        self.aim_target = Vector2D()

    def on_update(self, input: Input) -> None:
        # Os dois contadores primeiro, uma vez por frame cada. O
        # Cooldown nao tem como se defender de quem chama tick() duas
        # vezes -- quem conta os frames e este on_update.
        self.fire_cooldown.tick()
        self.flash.tick()

        self._move(input)

        # DEPOIS de mover, e isso importa. A camera esta pendurada aqui,
        # entao o enquadramento deste frame e o que sai da posicao nova;
        # mirar antes converteria o cursor com o enquadramento do frame
        # passado e a mira ficaria um frame atrasada do proprio jogador.
        self._aim()

        self._fire(input)

    def _move(self, input: Input) -> None:
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

    def _aim(self) -> None:
        # O cursor responde em coordenadas de TELA; o alvo tem de estar
        # em mundo. Quem sabe a diferenca e a camera, porque o
        # deslocamento e dela -- sem isso, cada no refaria a subtracao
        # da meia tela na mao e erraria perto da borda do mundo.
        self.aim_target = self.camera.screen_to_world(
            self.pointer.get_position()
        )

        to_target = self.aim_target - self.get_world_position()

        if to_target.magnitude() == 0.0:
            # Cursor exatamente sobre a origem do jogador. atan2(0, 0)
            # devolve 0.0, ou seja, o jogador daria um tranco para a
            # direita ao passar o mouse por cima de si mesmo. Manter a
            # ultima direcao e o comportamento que ninguem nota.
            return

        # A frente do jogador e o proprio eixo +X local -- convencao
        # DESTE jogo, e nao da engine. E o que faz o satelite, que mora
        # em (10, 0) local, virar o indicador visivel da mira sem uma
        # linha de codigo para isso.
        self.transform.rotation = math.atan2(to_target.y, to_target.x)

    def _fire(self, input: Input) -> None:
        if not self.actions.is_pressed(Action.FIRE, input):
            return

        if not self.fire_cooldown.is_ready():
            return

        # Sem projetil ainda: a bala e da semana 3. O que este frame
        # prova e a cadencia -- segurar o gatilho nao dispara todo
        # frame, e o botao do mouse e a tecla Z entram pela mesma acao.
        self.fire_cooldown.start()
        self.flash.start()

    def on_render(self, renderer: Renderer) -> None:
        # get_world_bounds, e nao get_world_position: draw_rect fala em
        # canto porque nao sabe girar, e a conversao a partir do anchor
        # e do VisualNode. Uma chamada so em vez de top_left + size:
        # sao duas subidas da hierarquia inteira contra uma.
        bounds = self.get_world_bounds()

        color = self.color if self.flash.is_ready() else FLASH_COLOR

        renderer.draw_rect(bounds.position, bounds.size, color)


class Satellite(VisualNode):
    # Sem uma linha sobre movimento de orbita: segue e gira em volta do
    # pai apenas por estar pendurado nele. O raio e a distancia local
    # ate a origem do pai -- que e o centro dele.
    #
    # E, de graca, virou o indicador da mira: morando em (10, 0) local,
    # ele fica sobre o eixo +X do jogador, que e a frente dele. Quando
    # o jogador aponta, o satelite aponta junto. Nao ha codigo para
    # isso -- e a transform hierarquica fazendo o trabalho.

    def __init__(self, name: str | None = None) -> None:
        super().__init__(name, size=Vector2D(4.0, 4.0))

        self.transform.position = Vector2D(10.0, 0.0)
        self.color = 8

    def on_update(self, input: Input) -> None:
        # O giro PROPRIO dele, que se compoe com o do pai: a orbita vem
        # do jogador, este aqui so roda em torno do proprio centro.
        self.transform.rotation += SATELLITE_SPIN

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

    def __init__(self, name: str, player: Player) -> None:
        super().__init__(name)

        self.player = player

    def on_render(self, renderer: Renderer) -> None:
        renderer.draw_text(Vector2D(4.0, 4.0), "WASD/SETAS mover", 7)
        renderer.draw_text(Vector2D(4.0, 12.0), "MOUSE/Z atirar", 7)

        position = self.player.get_world_position()
        target = self.player.aim_target

        # As duas leituras que interessam para conferir a semana 1: onde
        # o jogador esta e para onde ele acha que esta mirando, os dois
        # em coordenadas de MUNDO. Perto da borda do mundo uma conversao
        # tela -> mundo errada aparece justamente aqui, como um alvo que
        # descola do cursor.
        renderer.draw_text(
            Vector2D(4.0, SCREEN_HEIGHT - 18.0),
            f"pos x{int(position.x)} y{int(position.y)}",
            7,
        )
        renderer.draw_text(
            Vector2D(4.0, SCREEN_HEIGHT - 10.0),
            f"mira x{int(target.x)} y{int(target.y)}",
            7,
        )


class DemoScene(Scene):
    def __init__(self, name: str, pointer: Pointer) -> None:
        super().__init__(name)

        # A camera nasce ANTES do jogador agora, porque o jogador
        # precisa dela para converter tela -> mundo. A ordem de
        # construcao passou a dizer quem depende de quem.
        camera = Camera(
            "Camera",
            viewport_width=SCREEN_WIDTH,
            viewport_height=SCREEN_HEIGHT,
        )

        player = Player("Player", DEMO_BINDINGS, pointer, camera)
        player.transform.position = Vector2D(0.0, 0.0)

        satellite = Satellite("Satellite")

        player.add_child(satellite)

        # Pendurada no jogador: a camera o segue pela propria transform
        # hierarquica, sem codigo de follow.
        #
        # Em (0, 0) local, e isso deixou de ser detalhe: com a mira
        # escrevendo na rotacao do jogador, uma camera DESLOCADA seria
        # varrida pelo mundo a cada mexida do mouse -- o enquadramento
        # mudaria, o alvo convertido mudaria com ele, e a mira
        # perseguiria o proprio rabo. Centrada, girar nao move nada.
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

    # O ponteiro nao vai para a Engine, e de proposito: a Engine compoe
    # o que o LACO precisa -- cena, renderer e o input que o update
    # recebe --, e o cursor e lido por um no, que o pede no construtor.
    # Enfia-lo no `update` obrigaria todo no da arvore a carregar um
    # argumento que quase nenhum usa.
    pointer = PyxelPointer()

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
        # Sem isto nao se ve para onde se esta mirando: o Pyxel esconde
        # o cursor por default. Um jogo que desenhasse a propria mira
        # deixaria desligado.
        show_cursor=True,
    )

    game = Game(
        application=application,
        engine=engine,
        config=config,
        # O Game carrega a cena depois do initialize, para que o
        # on_enter encontre o backend ja de pe.
        initial_scene=DemoScene("Demo", pointer),
    )

    game.run()


if __name__ == "__main__":
    main()
