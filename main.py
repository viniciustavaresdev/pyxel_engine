import math
from enum import Enum, auto
from pathlib import Path

from engine import (
    ActionMap,
    ApplicationConfig,
    Body,
    Camera,
    Collision,
    Cooldown,
    Engine,
    Game,
    Input,
    Key,
    Node,
    Pointer,
    Rect,
    Renderer,
    Scene,
    SceneManager,
    TileSource,
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
from engine.adapters.pyxel.pyxel_tile_source import PyxelTileSource

SCREEN_WIDTH = 160
SCREEN_HEIGHT = 120
FPS = 60

# Ao lado deste arquivo, e nao relativo ao diretorio de trabalho: o
# botao Run de uma IDE parte de qualquer lugar, e um caminho relativo
# falharia em silencio -- bancos vazios, tilemap preto, nenhum erro.
RESOURCE_PATH = str(Path(__file__).with_name("assets.pyxres"))

# O andar mora no tilemap 0 do .pyxres. O banco do Pyxel tem 256x256
# tiles; o que esta DESENHADO e este canto dele, e e so isso que o
# Floor recorta para a tela.
FLOOR_TILEMAP = 0
FLOOR_COLUMNS = 39
FLOOR_ROWS = 24

# Quais tiles sao parede. DECISAO DO JOGO, nao da engine: a engine
# sabe o que e um tile, mas "solido" e uma afirmacao sobre esta arte
# -- e uma engine que decidisse isso estaria adivinhando qual desenho
# e parede. No banco de imagem, toda a linha 0 e parede: reta
# vertical, reta horizontal e os oito cantos e juncoes. A Collision
# recebe este conjunto pronto, e e a unica coisa que ela sabe sobre
# o significado de um tile.
SOLID_TILES = frozenset((column, 0) for column in range(1, 11))

# Nao existe mais um retangulo de mundo. O limite do jogador e a parede
# pintada em volta do andar -- e, fora do desenho, a borda do banco de
# tiles, que a Collision trata como solida.

PLAYER_SIZE = 8.0
PLAYER_IMAGE = 0
PLAYER_SPRITE = Rect(8.0, 16.0, 8.0, 8.0)
PLAYER_COLOR_KEY = 0
PLAYER_SPAWN = Vector2D(156.0, 156.0)
PLAYER_SPEED = 1.0

# Em FRAMES, como toda duracao daqui para frente. A 60 fps, 12 frames
# sao 0,2 s -- cinco tiros por segundo.
FIRE_COOLDOWN = 12

FLASH_FRAMES = 6
FLASH_COLOR = 7

GUN_SPRITE = Rect(8.0, 40.0, 8.0, 8.0)
GUN_IMAGE = 0
GUN_COLOR_KEY = 0

# O raio de debug da mira: ate onde ele vai, e as cores -- vermelho
# quando parou numa parede, verde num corpo, cinza quando acabou o
# alcance sem acertar nada.
AIM_RAY_RANGE = 64.0
AIM_RAY_COLOR = 10


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


class Player(Body):
    # Le o teclado pela porta Input e o cursor pela porta Pointer.
    # Nenhum `import pyxel` aqui: o no nao sabe em que backend esta
    # rodando, e nem que existe um mouse de verdade do outro lado.
    #
    # Body, que e um VisualNode que colide: a posicao do jogador e o
    # CENTRO dele, porque o anchor default e Anchor.CENTER. E o que faz
    # o satelite orbitar o meio do quadrado, a camera enquadrar o meio
    # do quadrado e a caixa de colisao ser a caixa desenhada, sem uma
    # linha de correcao em nenhum dos tres.

    def __init__(
        self,
        name: str,
        actions: ActionMap[Action],
        pointer: Pointer,
        camera: Camera,
        collision: Collision,
    ) -> None:
        super().__init__(name, size=Vector2D(PLAYER_SIZE, PLAYER_SIZE))

        # As dependencias chegam pelo construtor, e nenhuma e opcional.
        # Sao configuracao do jogo, nao estado global -- e exigi-las
        # obriga quem monta a cena a dizer de onde vem cada uma, em vez
        # de um default silencioso responder por ele.
        #
        # A camera esta aqui por um motivo so: ela e quem sabe converter
        # tela -> mundo. Nao e para mover nem para enquadrar. E a
        # colisao esta aqui porque e ela quem sabe onde ha parede: o
        # jogador diz para onde QUER ir, e ela diz ate onde da.
        self.actions = actions
        self.pointer = pointer
        self.camera = camera
        self.collision = collision

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

        # Substituiu o clamp num retangulo de mundo. O jogador nao
        # escreve mais na propria posicao ao andar: entrega o
        # deslocamento que quer, e a colisao escreve o que a parede
        # permitiu -- por eixo, entao a diagonal contra a parede
        # escorrega em vez de grudar.
        self.collision.move_and_slide(self, direction * PLAYER_SPEED)

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
        # O flash continua um retangulo: a porta nao troca a paleta de
        # um sprite, e um quadrado branco por alguns frames e o efeito
        # que se quer -- o jogador SOME num clarao, nao muda de cor.
        if not self.flash.is_ready():
            bounds = self.get_world_bounds()
            renderer.draw_rect(bounds.position, bounds.size, FLASH_COLOR)
            return

        # draw_sprite fala em CENTRO, porque gira -- e get_world_center
        # e exato para qualquer anchor. A rotacao e a mundial, nao a
        # local: se um dia o jogador for filho de algo que gira, o
        # sprite acompanha como o resto da hierarquia.

        renderer.draw_sprite(
            self.get_world_center(),
            PLAYER_IMAGE,
            PLAYER_SPRITE,
            color_key=PLAYER_COLOR_KEY,
            #rotation=world.rotation + PLAYER_SPRITE_TURN,
        )


class Gun(VisualNode):
    # Sem uma linha sobre movimento de orbita: segue e gira em volta do
    # pai apenas por estar pendurado nele. O raio e a distancia local
    # ate a origem do pai -- que e o centro dele.
    #
    # E, de graca, virou o indicador da mira: morando em (10, 0) local,
    # ele fica sobre o eixo +X do jogador, que e a frente dele. Quando
    # o jogador aponta, o satelite aponta junto. Nao ha codigo para
    # isso -- e a transform hierarquica fazendo o trabalho.

    def __init__(self, name: str | None = None) -> None:
        super().__init__(name, size=Vector2D(8.0, 8.0))

        self.transform.position = Vector2D(10.0, 0.0)
        self.color = 8

    def on_update(self, input: Input) -> None:
        pass

    def on_render(self, renderer: Renderer) -> None:
        
        renderer.draw_sprite(
            self.get_world_center(),
            GUN_IMAGE,
            GUN_SPRITE,
            color_key=GUN_COLOR_KEY,
            rotation=self.parent.transform.rotation,
        )


class Floor(Node):
    # O andar. Um Node, e nao um VisualNode: nao tem anchor nem gira, e
    # o tamanho dele e do tilemap, nao de uma caixa que a engine
    # resolveria. Substituiu os marcos de grade da demo antiga -- o
    # chao desenhado e um referencial melhor para ver a camera andar.
    #
    # Sem estado alem da porta de leitura: o Pyxel guarda os tiles, e o
    # que este no faz por frame e uma chamada de desenho. Nao existe
    # "carregar a fase" -- o `pyxel.load` do initialize ja fez isso.

    def __init__(self, name: str, tiles: TileSource) -> None:
        super().__init__(name)

        # A porta de LEITURA, so para converter tiles em pixels: a
        # regiao do draw_tilemap e em pixels, e o tamanho do tile e do
        # backend. Escrever 8 aqui funcionaria hoje e mentiria amanha.
        size = tiles.tile_size

        self.region = Rect(
            0.0,
            0.0,
            float(FLOOR_COLUMNS * size),
            float(FLOOR_ROWS * size),
        )

    def on_render(self, renderer: Renderer) -> None:
        # Canto em (0, 0) do mundo: o tile (c, l) do mapa cai nos pixels
        # (c * 8, l * 8), e a mesma conta vale para a colisao. Regiao
        # inteira, todo frame -- o backend recorta o que a camera nao
        # ve, e um so bltm e mais barato que calcular a fatia visivel.
        renderer.draw_tilemap(Vector2D(), FLOOR_TILEMAP, self.region)


class AimRay(Node):
    # O raio de debug da semana 2: sai do centro do jogador na direcao
    # em que ele aponta e para na primeira parede -- ou no primeiro
    # corpo, quando houver um. Um Node na camada world, e nao filho do
    # jogador: o raio e uma pergunta ao MUNDO, e desenhar o ponto em
    # que ele parou e desenhar em coordenadas de mundo.
    #
    # E o primeiro uso do raycast, e nao o motivo dele existir. A
    # semana 3 vai lanca-lo da bala e dos olhos do inimigo com a mesma
    # chamada -- inclusive o `ignore`, que aqui exclui o proprio
    # jogador, porque o raio nasce dentro da caixa dele.

    def __init__(
        self, name: str, player: Player, collision: Collision
    ) -> None:
        super().__init__(name)

        self.player = player
        self.collision = collision

    def on_render(self, renderer: Renderer) -> None:
        # A frente do jogador e o eixo +X local dele, girado pela
        # rotacao -- a mesma convencao que o satelite segue de graca.
        rotation = self.player.transform.rotation
        direction = Vector2D(math.cos(rotation), math.sin(rotation))

        origin = self.player.get_world_position()

        hit = self.collision.raycast(
            origin,
            direction,
            AIM_RAY_RANGE,
            ignore=(self.player,),
        )

        if hit is None:
            return

        renderer.draw_rect(
            hit.point - Vector2D(1.0, 1.0), Vector2D(2.0, 2.0), AIM_RAY_COLOR
        )


class Hud(Node):
    # Desenha em coordenadas de TELA -- e nao faz nada para isso. Vive
    # na camada `ui` da cena, e e a cena que sai do enquadramento antes
    # da passada dela.
    #
    # Antes, este no chamava reset_camera() no proprio on_render e
    # dependia de ser o ultimo filho a desenhar: estado global do
    # renderer alterado no meio da travessia, com uma ordem que ninguem
    # declarava em lugar nenhum.

    def __init__(
        self, name: str, player: Player, collision: Collision
    ) -> None:
        super().__init__(name)

        self.player = player
        self.collision = collision

    def on_render(self, renderer: Renderer) -> None:
        renderer.draw_text(Vector2D(4.0, 4.0), "WASD/SETAS mover", 7)
        renderer.draw_text(Vector2D(4.0, 12.0), "MOUSE/Z atirar", 7)

        position = self.player.get_world_position()
        target = self.player.aim_target

        # A conta de mundo -> celula mora na Collision, escrita uma vez.
        # O HUD so pergunta.
        column, row = self.collision.cell_at(position)
        solid = self.collision.is_solid(column, row)

        # Tres leituras: onde o jogador esta e para onde mira (semana 1,
        # em coordenadas de MUNDO), e a celula sob ele (semana 2). Com
        # a colisao ligada a terceira nunca deve dizer PAREDE: se
        # disser, o move_and_slide deixou passar.
        renderer.draw_text(
            Vector2D(4.0, SCREEN_HEIGHT - 26.0),
            f"pos x{int(position.x)} y{int(position.y)}",
            7,
        )
        renderer.draw_text(
            Vector2D(4.0, SCREEN_HEIGHT - 18.0),
            f"mira x{int(target.x)} y{int(target.y)}",
            7,
        )
        renderer.draw_text(
            Vector2D(4.0, SCREEN_HEIGHT - 10.0),
            f"cel {column},{row} {'PAREDE' if solid else ''}",
            8 if solid else 7,
        )


class DemoScene(Scene):
    def __init__(self, name: str, pointer: Pointer, tiles: TileSource) -> None:
        super().__init__(name)

        # A geometria do andar: a porta de leitura mais a decisao do
        # jogo sobre o que e parede. Uma so, compartilhada por quem
        # anda e por quem pergunta -- hoje o jogador e o HUD, na
        # semana 3 o inimigo e a bala.
        collision = Collision(tiles, SOLID_TILES)

        # O chao entra PRIMEIRO na camada world: a ordem de desenho e a
        # ordem da arvore, e o andar tem de sair sob o jogador. E o
        # unico lugar da demo em que a posicao na lista importa -- ate
        # o z_index da semana 3 chegar.
        self.world.add_child(Floor("Floor", tiles))

        # A camera nasce ANTES do jogador agora, porque o jogador
        # precisa dela para converter tela -> mundo. A ordem de
        # construcao passou a dizer quem depende de quem.
        camera = Camera(
            "Camera",
            viewport_width=SCREEN_WIDTH,
            viewport_height=SCREEN_HEIGHT,
        )

        player = Player("Player", DEMO_BINDINGS, pointer, camera, collision)
        player.transform.position = PLAYER_SPAWN

        gun = Gun("gun")

        player.add_child(gun)

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

        # Registrado como corpo: e o que faz o raycast e o bodies_in o
        # enxergarem. Mover contra a parede nao exigia isso; ser
        # ATINGIDO exige. A lista e mantida pelo jogo ate os grupos da
        # semana 3 apoiarem-na na arvore.
        collision.add_body(player)

        # Cada um na camada que diz em que espaco desenha. A UI desenha
        # depois do mundo porque e a cena que decide isso, e nao a
        # posicao na lista de filhos. O raio vem DEPOIS do jogador para
        # o marcador sair por cima dele.
        self.world.add_child(player)
        self.world.add_child(AimRay("AimRay", player, collision))
        self.ui.add_child(Hud("Hud", player, collision))


def main() -> None:

    application = PyxelApplication()

    scene_manager = SceneManager()

    renderer = PyxelRenderer()

    input = PyxelInput()

    pointer = PyxelPointer()

    tiles = PyxelTileSource(FLOOR_TILEMAP)

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
        resource_path=RESOURCE_PATH,
        show_cursor=True,
    )

    game = Game(
        application=application,
        engine=engine,
        config=config,
        # O Game carrega a cena depois do initialize, para que o
        # on_enter encontre o backend ja de pe.
        initial_scene=DemoScene("Demo", pointer, tiles),
    )

    game.run()


if __name__ == "__main__":
    main()
