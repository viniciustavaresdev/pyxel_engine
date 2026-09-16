"""Superficie publica da engine.

O que esta reexportado aqui e CONTRATO: um jogo pode contar com estes
nomes e com estes caminhos. O que nao esta e detalhe interno, livre
para mudar de modulo ou de pasta sem aviso.

Os ADAPTADORES ficam de fora de proposito, e nao por esquecimento.
Reexportar `PyxelRenderer` aqui faria `import engine` executar
`import pyxel` -- e a promessa de que o nucleo nao conhece o backend
passaria a valer por acidente, ate o dia em que alguem rodasse a suite
numa maquina sem o Pyxel instalado. Deixando-os fora, a fronteira
aparece na propria forma de importar:

    from engine import Node, Vector2D              # nucleo
    from engine.adapters.pyxel.pyxel_renderer import PyxelRenderer

A linha mais longa e a que amarra o jogo a um backend. E bom que doa
um pouco.
"""

from engine.input.action_map import ActionMap
from engine.input.key import Key
from engine.math.anchor import Anchor
from engine.math.rect import Rect
from engine.math.transform import Transform
from engine.math.vector2d import Vector2D
from engine.physics.collision import Collision
from engine.physics.raycast_hit import RaycastHit
from engine.ports.application import Application
from engine.ports.input import Input
from engine.ports.pointer import Pointer
from engine.ports.renderer import Renderer
from engine.ports.tile_source import TileSource
from engine.runtime.application_config import ApplicationConfig
from engine.runtime.cooldown import Cooldown
from engine.runtime.engine import Engine
from engine.runtime.game import Game
from engine.scene.body import Body
from engine.scene.camera import Camera
from engine.scene.node import Node
from engine.scene.scene import Scene
from engine.scene.scene_manager import SceneManager
from engine.scene.visual_node import VisualNode

__all__ = [
    # math -- valores puros
    "Anchor",
    "Rect",
    "Transform",
    "Vector2D",
    # scene -- a arvore
    "Body",
    "Camera",
    "Node",
    "Scene",
    "SceneManager",
    "VisualNode",
    # runtime -- o laco de frame
    "ApplicationConfig",
    "Cooldown",
    "Engine",
    "Game",
    # physics -- caixas contra a grade
    "Collision",
    "RaycastHit",
    # input
    "ActionMap",
    "Key",
    # ports -- para quem escreve um adaptador ou um duble de teste
    "Application",
    "Input",
    "Pointer",
    "Renderer",
    "TileSource",
]
