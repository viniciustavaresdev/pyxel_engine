from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ApplicationConfig:
    width: int
    height: int
    title: str

    # 30 e o default do proprio Pyxel. Explicito aqui porque este
    # numero GOVERNA A FISICA: sem dt, um update e um frame, e as
    # velocidades do jogo sao por frame. Trocar 60 por 30 aqui nao
    # muda a suavidade, muda a velocidade de tudo -- pela metade.
    #
    # E o preco declarado de nao medir tempo: a taxa deixou de ser
    # detalhe do backend e virou parte do contrato do jogo.
    fps: int = 30

    # Caminho de um .pyxres. Sem recurso carregado os bancos de imagem
    # ficam vazios e draw_sprite desenha nada -- em silencio, que e o
    # pior modo de falhar.
    resource_path: str | None = None

    # O cursor do sistema aparece sobre a janela?
    #
    # Mora aqui, e nao na porta `Pointer`, porque sao perguntas
    # diferentes: a porta responde ONDE o cursor esta, e isso vale com
    # ele visivel ou nao. Ligar o desenho dele e decisao de JANELA, e
    # janela e o que o `Application` configura -- mesmo lugar e mesma
    # forma do `resource_path`.
    #
    # Default False porque e o do proprio Pyxel, e porque um jogo so de
    # teclado nao deve ganhar um cursor por acidente. Quem mira com o
    # mouse liga -- ou desenha a propria mira e deixa desligado.
    show_cursor: bool = False
