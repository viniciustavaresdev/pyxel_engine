"""A superficie publica declarada em engine/__init__.py.

O que esta em `__all__` e contrato. Estes testes cobram as duas
promessas que o contrato faz: que os nomes existem, e que importa-los
nao arrasta o backend junto.
"""

import subprocess
import sys

import engine


class TestTheDeclaredSurface:

    def test_every_announced_name_exists(self):
        # Um nome no __all__ que nao resolve so apareceria no import de
        # quem usa a engine -- e com uma mensagem que nao aponta para
        # a lista errada.
        missing = [
            name for name in engine.__all__ if not hasattr(engine, name)
        ]

        assert missing == []

    def test_no_name_is_announced_twice(self):
        # Duplicata em __all__ nao levanta erro nenhum -- so fica la,
        # ate alguem reorganizar a lista e apagar a ocorrencia errada.
        assert len(engine.__all__) == len(set(engine.__all__))

    def test_no_adapter_leaks_into_the_surface(self):
        # Reexportar um adaptador aqui seria o caminho mais curto para
        # `import engine` passar a exigir o Pyxel.
        leaked = [name for name in engine.__all__ if name.startswith("Pyxel")]

        assert leaked == []

    def test_the_core_names_are_reachable(self):
        from engine import Node, Scene, Vector2D, VisualNode

        assert issubclass(VisualNode, Node)
        assert issubclass(Scene, Node)
        assert Vector2D(1.0, 2.0).x == 1.0


class TestImportingTheEngineDoesNotDragTheBackend:
    """A promessa estrutural: o nucleo nao conhece o Pyxel.

    Em subprocesso porque `sys.modules` e do processo inteiro -- neste
    aqui o Pyxel ja foi carregado pelos testes de adaptador, entao
    perguntar direto responderia sobre a ordem dos testes e nao sobre a
    engine.
    """

    def _pyxel_is_loaded_after(self, statement: str) -> bool:
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                f"import sys; {statement}; print('pyxel' in sys.modules)",
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        return result.stdout.strip() == "True"

    def test_importing_engine_does_not_import_pyxel(self):
        assert self._pyxel_is_loaded_after("import engine") is False

    def test_importing_the_core_names_does_not_import_pyxel(self):
        assert (
            self._pyxel_is_loaded_after(
                "from engine import Node, Scene, Vector2D"
            )
            is False
        )

    def test_importing_an_adapter_does_import_pyxel(self):
        # O contraponto: se este passar a dar False, a checagem acima
        # virou vacua -- estaria provando que o Pyxel nunca carrega, e
        # nao que o nucleo o dispensa.
        statement = (
            "from engine.adapters.pyxel.pyxel_renderer import PyxelRenderer"
        )

        assert self._pyxel_is_loaded_after(statement) is True
