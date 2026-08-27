from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ApplicationConfig:

    width: int
    height: int
    title: str

    # 30 e o default do proprio Pyxel. Explicito aqui porque o dt do
    # jogo depende disto, e um numero que so existe dentro do backend
    # nao pode governar a fisica.
    fps: int = 30

    # Caminho de um .pyxres. Sem recurso carregado os bancos de imagem
    # ficam vazios e draw_sprite desenha nada -- em silencio, que e o
    # pior modo de falhar.
    resource_path: str | None = None
