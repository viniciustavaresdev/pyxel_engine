import dataclasses
import math

import pytest

from engine.math.transform import Transform
from engine.math.vector2d import Vector2D
from engine.scene.node import Node
from engine.scene.scene import Scene
from tests.conftest import SpyNode


def uncached_world_transform(node: Node) -> Transform:
    """A transform mundial calculada do zero, sem olhar cache nenhum.

    E a implementacao do passo 7, mantida aqui como oraculo: um cache
    so pode ser testado contra a resposta que ele deveria ter dado.
    """
    if node.parent is None:
        return node.transform.copy()

    return uncached_world_transform(node.parent).compose(node.transform)


class CountingNode(Node):
    """Conta quantas vezes a PROPRIA transform mundial foi resolvida."""

    def __init__(self, name: str | None = None) -> None:
        super().__init__(name)

        self.resolutions = 0

    def get_world_transform(self) -> Transform:
        self.resolutions += 1

        return super().get_world_transform()


class TestAddChild:
    def test_sets_parent_and_appends(self):
        parent = Node("Parent")
        child = Node("Child")

        parent.add_child(child)

        assert child.parent is parent
        assert parent.children == [child]

    def test_keeps_insertion_order(self):
        # A ordem de insercao e a ordem de update e de desenho. Ate
        # existir z-index, ela e a unica coisa que decide quem fica
        # por cima.
        parent = Node("Parent")
        first = Node("First")
        second = Node("Second")

        parent.add_child(first)
        parent.add_child(second)

        assert parent.children == [first, second]

    def test_reparenting_detaches_from_previous_parent(self):
        old_parent = Node("Old")
        new_parent = Node("New")
        child = Node("Child")

        old_parent.add_child(child)
        new_parent.add_child(child)

        assert child.parent is new_parent
        assert child not in old_parent.children
        assert new_parent.children == [child]

    def test_rejects_self_as_child(self):
        node = Node("Node")

        with pytest.raises(ValueError):
            node.add_child(node)

    def test_rejects_cycle(self):
        # Sem esta guarda, update() entraria em recursao infinita.
        grandparent = Node("Grandparent")
        parent = Node("Parent")
        child = Node("Child")

        grandparent.add_child(parent)
        parent.add_child(child)

        with pytest.raises(ValueError):
            child.add_child(grandparent)


class TestRemoveChild:
    def test_detaches_child(self):
        parent = Node("Parent")
        child = Node("Child")
        parent.add_child(child)

        parent.remove_child(child)

        assert child.parent is None
        assert parent.children == []

    def test_removing_a_stranger_is_a_no_op(self):
        parent = Node("Parent")
        other_parent = Node("Other")
        stranger = Node("Stranger")
        other_parent.add_child(stranger)

        parent.remove_child(stranger)

        assert stranger.parent is other_parent
        assert other_parent.children == [stranger]


class TestIsAncestorOf:
    def test_true_for_direct_parent(self):
        parent = Node("Parent")
        child = Node("Child")
        parent.add_child(child)

        assert parent.is_ancestor_of(child)

    def test_true_for_grandparent(self):
        grandparent = Node("Grandparent")
        parent = Node("Parent")
        child = Node("Child")
        grandparent.add_child(parent)
        parent.add_child(child)

        assert grandparent.is_ancestor_of(child)

    def test_false_for_child(self):
        parent = Node("Parent")
        child = Node("Child")
        parent.add_child(child)

        assert not child.is_ancestor_of(parent)

    def test_false_for_self(self):
        node = Node("Node")

        assert not node.is_ancestor_of(node)

    def test_false_for_sibling(self):
        parent = Node("Parent")
        left = Node("Left")
        right = Node("Right")
        parent.add_child(left)
        parent.add_child(right)

        assert not left.is_ancestor_of(right)


def build_tree(log):
    """World -> Player -> (Weapon, Shadow)."""
    world = SpyNode("World", log)
    player = SpyNode("Player", log)
    weapon = SpyNode("Weapon", log)
    shadow = SpyNode("Shadow", log)

    world.add_child(player)
    player.add_child(weapon)
    player.add_child(shadow)

    return world


class TestTraversalOrder:
    def test_update_is_pre_order(self, log, spy_input):
        # O pai atualiza ANTES dos filhos: um filho que le o estado do
        # pai no mesmo frame ve o valor ja atualizado.
        build_tree(log).update(spy_input)

        assert log == [
            ("update", "World"),
            ("update", "Player"),
            ("update", "Weapon"),
            ("update", "Shadow"),
        ]

    def test_render_is_pre_order(self, log, renderer):
        # Pai desenha antes dos filhos, entao o filho fica por cima.
        build_tree(log).render(renderer)

        assert log == [
            ("render", "World"),
            ("render", "Player"),
            ("render", "Weapon"),
            ("render", "Shadow"),
        ]

    def test_enter_is_pre_order(self, log):
        build_tree(log).enter()

        assert log == [
            ("enter", "World"),
            ("enter", "Player"),
            ("enter", "Weapon"),
            ("enter", "Shadow"),
        ]

    def test_exit_is_post_order(self, log):
        # Espelho do enter: o filho se desmonta antes do pai, entao
        # ainda pode contar com o pai vivo durante o proprio on_exit.
        world = build_tree(log)
        log.clear()

        world.exit()

        assert log == [
            ("exit", "Weapon"),
            ("exit", "Shadow"),
            ("exit", "Player"),
            ("exit", "World"),
        ]

    def test_one_update_is_one_frame_for_every_node(self, log, spy_input):
        # O que este teste afirmava antes: que o dt chegava intacto a
        # cada no. Sem dt, o que sobra para garantir e mais forte -- um
        # update da arvore e exatamente um on_update por no, sem
        # repeticao de compensacao e sem ninguem pulado.
        world = build_tree(log)

        world.update(spy_input)
        world.update(spy_input)

        assert log.count(("update", "Player")) == 2
        assert len(log) == 8


class TestRenderPropagation:
    def test_the_same_renderer_reaches_the_leaves(self, renderer):
        class Drawer(Node):
            def on_render(self, renderer):
                renderer.draw_rect(Vector2D(1.0, 2.0), Vector2D(3.0, 4.0), 5)

        parent = Node("Parent")
        parent.add_child(Drawer("Drawer"))

        parent.render(renderer)

        assert renderer.calls == [("draw_rect", 1.0, 2.0, 3.0, 4.0, 5)]


class TestWorldPosition:
    def test_root_returns_its_own_position(self):
        node = Node("Node")
        node.transform.position = Vector2D(10.0, 20.0)

        assert node.get_world_position() == Vector2D(10.0, 20.0)

    def test_the_returned_position_cannot_move_the_node(self):
        # Antes o risco era real: quem chamasse podia mover o no so por
        # escrever no resultado. Com Vector2D imutavel a garantia deixa
        # de depender de o get_world_position lembrar de copiar.
        node = Node("Node")

        world = node.get_world_position()

        with pytest.raises(dataclasses.FrozenInstanceError):
            world.x = 99.0  # type: ignore[misc]

        assert node.transform.position == Vector2D(0.0, 0.0)

    def test_child_is_offset_by_the_parent(self):
        parent = Node("Parent")
        child = Node("Child")
        parent.transform.position = Vector2D(100.0, 50.0)
        child.transform.position = Vector2D(10.0, 5.0)
        parent.add_child(child)

        assert child.get_world_position() == Vector2D(110.0, 55.0)

    def test_offsets_accumulate_down_the_chain(self):
        nodes = [Node(f"Node{i}") for i in range(4)]

        for node in nodes:
            node.transform.position = Vector2D(1.0, 2.0)

        # strict=False explicito: as duas listas tem tamanhos
        # diferentes de proposito -- e o deslocamento de um que forma
        # os pares pai/filho.
        for parent, child in zip(nodes, nodes[1:], strict=False):
            parent.add_child(child)

        assert nodes[-1].get_world_position() == Vector2D(4.0, 8.0)

    def test_detached_child_falls_back_to_its_local_position(self):
        parent = Node("Parent")
        child = Node("Child")
        parent.transform.position = Vector2D(100.0, 50.0)
        child.transform.position = Vector2D(10.0, 5.0)
        parent.add_child(child)
        parent.remove_child(child)

        assert child.get_world_position() == Vector2D(10.0, 5.0)


class TestWorldTransformComposition:
    def test_parent_scale_stretches_the_child_offset(self):
        parent = Node("Parent")
        child = Node("Child")
        parent.transform.scale = Vector2D(2.0, 2.0)
        child.transform.position = Vector2D(10.0, 0.0)
        parent.add_child(child)

        assert child.get_world_position() == Vector2D(20.0, 0.0)

    def test_parent_rotation_orbits_the_child(self):
        parent = Node("Parent")
        child = Node("Child")
        parent.transform.rotation = math.pi / 2.0
        child.transform.position = Vector2D(10.0, 0.0)
        parent.add_child(child)

        world = child.get_world_position()

        assert world.x == pytest.approx(0.0, abs=1e-9)
        assert world.y == pytest.approx(10.0)

    def test_scale_is_applied_before_rotation(self):
        # A ordem e o ponto: escalar depois de girar poria o filho em
        # (0, 10) esticado no eixo errado.
        parent = Node("Parent")
        child = Node("Child")
        parent.transform.scale = Vector2D(3.0, 1.0)
        parent.transform.rotation = math.pi / 2.0
        child.transform.position = Vector2D(10.0, 0.0)
        parent.add_child(child)

        world = child.get_world_position()

        assert world.x == pytest.approx(0.0, abs=1e-9)
        assert world.y == pytest.approx(30.0)

    def test_parent_translation_is_applied_last(self):
        parent = Node("Parent")
        child = Node("Child")
        parent.transform.position = Vector2D(100.0, 100.0)
        parent.transform.rotation = math.pi / 2.0
        child.transform.position = Vector2D(10.0, 0.0)
        parent.add_child(child)

        world = child.get_world_position()

        assert world.x == pytest.approx(100.0)
        assert world.y == pytest.approx(110.0)

    def test_rotation_accumulates_down_the_chain(self):
        parent = Node("Parent")
        child = Node("Child")
        parent.transform.rotation = math.pi / 4.0
        child.transform.rotation = math.pi / 4.0
        parent.add_child(child)

        assert child.get_world_transform().rotation == pytest.approx(
            math.pi / 2.0
        )

    def test_scale_accumulates_down_the_chain(self):
        parent = Node("Parent")
        child = Node("Child")
        parent.transform.scale = Vector2D(2.0, 3.0)
        child.transform.scale = Vector2D(4.0, 5.0)
        parent.add_child(child)

        assert child.get_world_transform().scale == Vector2D(8.0, 15.0)

    def test_world_transform_does_not_alias_the_local_one(self):
        # O Transform continua mutavel, entao esta garantia continua
        # valendo pelo copy() -- e nao de graca como a do Vector2D.
        node = Node("Node")

        world = node.get_world_transform()
        world.position = Vector2D(99.0, 99.0)
        world.scale = Vector2D(99.0, 99.0)

        assert node.transform.position == Vector2D(0.0, 0.0)
        assert node.transform.scale == Vector2D(1.0, 1.0)

    def test_a_node_is_unaffected_by_its_own_rotation(self):
        # Girar um no move os filhos dele, nunca ele proprio.
        node = Node("Node")
        node.transform.position = Vector2D(10.0, 0.0)
        node.transform.rotation = math.pi

        assert node.get_world_position() == Vector2D(10.0, 0.0)


class TestLifecycleOnLiveTree:
    def test_add_child_to_a_live_tree_fires_enter(self, log):
        parent = SpyNode("Parent", log)
        parent.enter()
        log.clear()

        parent.add_child(SpyNode("Child", log))

        assert log == [("enter", "Child")]

    def test_add_child_enters_the_whole_incoming_subtree(self, log):
        parent = SpyNode("Parent", log)
        parent.enter()
        branch = SpyNode("Branch", log)
        branch.add_child(SpyNode("Leaf", log))
        log.clear()

        parent.add_child(branch)

        assert log == [("enter", "Branch"), ("enter", "Leaf")]

    def test_add_child_to_a_cold_tree_does_not_fire_enter(self, log):
        # A arvore montada antes do change_scene tem de ficar quieta:
        # quem acorda todo mundo, uma vez so, e o enter() da cena.
        parent = SpyNode("Parent", log)

        parent.add_child(SpyNode("Child", log))

        assert log == []

    def test_remove_child_from_a_live_tree_fires_exit(self, log):
        parent = SpyNode("Parent", log)
        child = SpyNode("Child", log)
        parent.add_child(child)
        parent.enter()
        log.clear()

        parent.remove_child(child)

        assert log == [("exit", "Child")]

    def test_remove_child_from_a_cold_tree_does_not_fire_exit(self, log):
        parent = SpyNode("Parent", log)
        child = SpyNode("Child", log)
        parent.add_child(child)

        parent.remove_child(child)

        assert log == []

    def test_reparenting_between_live_trees_exits_then_enters(self, log):
        old_parent = SpyNode("Old", log)
        new_parent = SpyNode("New", log)
        old_parent.enter()
        new_parent.enter()
        child = SpyNode("Child", log)
        old_parent.add_child(child)
        log.clear()

        new_parent.add_child(child)

        assert log == [("exit", "Child"), ("enter", "Child")]


class TestIsInsideTree:
    def test_starts_outside(self):
        assert Node("Node").is_inside_tree is False

    def test_enter_puts_the_whole_subtree_inside(self):
        parent = Node("Parent")
        child = Node("Child")
        parent.add_child(child)

        parent.enter()

        assert parent.is_inside_tree is True
        assert child.is_inside_tree is True

    def test_exit_takes_the_whole_subtree_out(self):
        parent = Node("Parent")
        child = Node("Child")
        parent.add_child(child)
        parent.enter()

        parent.exit()

        assert parent.is_inside_tree is False
        assert child.is_inside_tree is False

    def test_removed_child_is_outside_again(self):
        parent = Node("Parent")
        child = Node("Child")
        parent.add_child(child)
        parent.enter()

        parent.remove_child(child)

        assert child.is_inside_tree is False


class TestActive:
    def test_active_by_default(self):
        assert Node("Node").active is True

    def test_inactive_node_does_not_update(self, log, spy_input):
        node = SpyNode("Node", log)
        node.active = False

        node.update(spy_input)

        assert log == []

    def test_inactive_node_freezes_its_subtree(self, log, spy_input):
        parent = SpyNode("Parent", log)
        parent.add_child(SpyNode("Child", log))
        parent.active = False

        parent.update(spy_input)

        assert log == []

    def test_inactive_node_still_renders(self, log, renderer):
        # active e visible sao independentes: pausar um inimigo nao
        # pode faze-lo sumir da tela.
        node = SpyNode("Node", log)
        node.active = False

        node.render(renderer)

        assert log == [("render", "Node")]

    def test_siblings_of_an_inactive_node_keep_updating(self, log, spy_input):
        parent = SpyNode("Parent", log)
        frozen = SpyNode("Frozen", log)
        frozen.active = False
        parent.add_child(frozen)
        parent.add_child(SpyNode("Awake", log))

        parent.update(spy_input)

        assert log == [
            ("update", "Parent"),
            ("update", "Awake"),
        ]


class TestVisible:
    def test_visible_by_default(self):
        assert Node("Node").visible is True

    def test_invisible_node_does_not_render(self, log, renderer):
        node = SpyNode("Node", log)
        node.visible = False

        node.render(renderer)

        assert log == []

    def test_invisible_node_hides_its_subtree(self, log, renderer):
        parent = SpyNode("Parent", log)
        parent.add_child(SpyNode("Child", log))
        parent.visible = False

        parent.render(renderer)

        assert log == []

    def test_invisible_node_still_updates(self, log, spy_input):
        node = SpyNode("Node", log)
        node.visible = False

        node.update(spy_input)

        assert log == [("update", "Node")]


class TestMutationDuringTraversal:
    def test_a_node_removing_itself_does_not_skip_the_next_sibling(
        self, log, spy_input
    ):
        class SelfRemover(Node):
            def on_update(self, input):
                assert self.parent is not None
                self.parent.remove_child(self)

        parent = Node("Parent")
        parent.add_child(SelfRemover("Remover"))
        parent.add_child(SpyNode("Witness", log))

        parent.update(spy_input)

        assert ("update", "Witness") in log

    def test_a_removed_sibling_does_not_update_after_removal(
        self, log, spy_input
    ):
        class Killer(Node):
            def __init__(self, name, target):
                super().__init__(name)
                self.target = target

            def on_update(self, input):
                assert self.parent is not None
                self.parent.remove_child(self.target)

        parent = Node("Parent")
        victim = SpyNode("Victim", log)
        parent.add_child(Killer("Killer", victim))
        parent.add_child(victim)

        parent.update(spy_input)

        assert log == []

    def test_a_child_added_during_update_waits_for_the_next_frame(
        self, log, spy_input
    ):
        # Um tiro criado no meio do frame nao pode ja andar nesse mesmo
        # frame: senao a distancia percorrida depende da ordem em que
        # os irmaos foram visitados.
        class Spawner(Node):
            def __init__(self, name, log):
                super().__init__(name)
                self.log = log
                self.spawned = False

            def on_update(self, input):
                if not self.spawned:
                    self.spawned = True
                    assert self.parent is not None
                    self.parent.add_child(SpyNode("Spawned", self.log))

        parent = Node("Parent")
        parent.add_child(Spawner("Spawner", log))

        parent.update(spy_input)
        assert log == []

        parent.update(spy_input)
        assert log == [("update", "Spawned")]


class TestQueueFree:
    def test_queued_node_survives_the_current_frame(self, spy_input):
        # Ele termina o frame: o on_update dele ainda roda por inteiro.
        class Suicidal(Node):
            def on_update(self, input):
                self.queue_free()

        parent = Node("Parent")
        node = Suicidal("Suicidal")
        parent.add_child(node)

        parent.update(spy_input)

        assert node.parent is None
        assert parent.children == []

    def test_queued_node_is_gone_on_the_next_frame(self, log, spy_input):
        class Suicidal(SpyNode):
            def on_update(self, input):
                super().on_update(input)
                self.queue_free()

        parent = Node("Parent")
        parent.add_child(Suicidal("Suicidal", log))

        parent.update(spy_input)
        parent.update(spy_input)

        assert log == [("update", "Suicidal")]

    def test_queue_free_fires_exit_on_a_live_tree(self, log, spy_input):
        parent = SpyNode("Parent", log)
        child = SpyNode("Child", log)
        parent.add_child(child)
        parent.enter()
        log.clear()

        child.queue_free()
        parent.update(spy_input)

        assert ("exit", "Child") in log

    def test_queue_free_does_not_disturb_the_siblings(self, log, spy_input):
        parent = Node("Parent")
        doomed = SpyNode("Doomed", log)
        survivor = SpyNode("Survivor", log)
        parent.add_child(doomed)
        parent.add_child(survivor)

        doomed.queue_free()
        parent.update(spy_input)

        assert parent.children == [survivor]

    def test_readopting_a_freed_node_clears_the_mark(self, log, spy_input):
        # Sem o reset, o no morreria de novo no primeiro frame do
        # novo pai -- e isso e reciclagem de bala em pool.
        parent = Node("Parent")
        other_parent = Node("Other")
        node = SpyNode("Node", log)
        parent.add_child(node)

        node.queue_free()
        parent.update(spy_input)
        other_parent.add_child(node)
        log.clear()

        other_parent.update(spy_input)

        assert log == [("update", "Node")]
        assert other_parent.children == [node]


class TestQueueFreeIsCollectedAtTheRoot:
    """A fila mora na raiz, nao em cada pai.

    Uma fila por pai so era esvaziada dentro do update daquele pai --
    e update retorna cedo quando `active` e falso. O resultado era um
    no marcado que sobrevivia indefinidamente dentro de um ramo
    pausado, e que continuava sendo DESENHADO, porque render nao olha
    `active`.
    """

    def test_a_node_inside_an_inactive_branch_is_still_collected(
        self, spy_input
    ):
        root = Node("Root")
        branch = Node("Branch")
        leaf = Node("Leaf")
        root.add_child(branch)
        branch.add_child(leaf)
        root.enter()

        leaf.queue_free()
        branch.active = False

        root.update(spy_input)

        assert leaf.parent is None
        assert branch.children == []

    def test_the_collected_node_leaves_the_tree_for_real(self, spy_input):
        # O sintoma que doia: o no continuava com _inside_tree e
        # continuava aparecendo na tela.
        root = Node("Root")
        branch = Node("Branch")
        leaf = Node("Leaf")
        root.add_child(branch)
        branch.add_child(leaf)
        root.enter()

        leaf.queue_free()
        branch.active = False
        root.update(spy_input)

        assert leaf.is_inside_tree is False

    def test_a_node_deep_in_the_tree_is_collected_by_the_root(self, spy_input):
        nodes = [Node(f"Node{i}") for i in range(5)]

        for parent, child in zip(nodes, nodes[1:], strict=False):
            parent.add_child(child)

        nodes[-1].queue_free()
        nodes[0].update(spy_input)

        assert nodes[-2].children == []

    def test_collection_happens_after_the_whole_traversal(
        self, log, spy_input
    ):
        # O no marcado no primeiro on_update do frame nao pode sumir no
        # meio do percurso: os irmaos seguintes ainda contam com ele.
        class Killer(Node):
            def __init__(self, name, target):
                super().__init__(name)
                self.target = target

            def on_update(self, input):
                self.target.queue_free()

        class Witness(Node):
            def __init__(self, name, target, log):
                super().__init__(name)
                self.target = target
                self.log = log

            def on_update(self, input):
                self.log.append(("saw", self.target.parent is not None))

        root = Node("Root")
        victim = Node("Victim")
        root.add_child(victim)
        root.add_child(Killer("Killer", victim))
        root.add_child(Witness("Witness", victim, log))

        root.update(spy_input)

        assert log == [("saw", True)]
        assert victim.parent is None


class TestQueueFreeBookkeeping:
    def test_queueing_twice_removes_once(self, spy_input):
        root = Node("Root")
        node = Node("Node")
        root.add_child(node)

        node.queue_free()
        node.queue_free()

        assert len(root._pending_removals) == 1

    def test_is_queued_for_removal_reports_the_mark(self):
        root = Node("Root")
        node = Node("Node")
        root.add_child(node)

        assert node.is_queued_for_removal is False

        node.queue_free()

        assert node.is_queued_for_removal is True

    def test_a_node_removed_by_hand_before_the_flush_is_left_alone(
        self, spy_input
    ):
        # Marcado, retirado na mao, e readotado antes da coleta. Sem a
        # guarda, a coleta o arrancaria da arvore NOVA -- que nunca
        # pediu nada.
        root = Node("Root")
        other = Node("Other")
        node = Node("Node")
        root.add_child(node)

        node.queue_free()
        root.remove_child(node)
        other.add_child(node)

        root.update(spy_input)

        assert node.parent is other
        assert other.children == [node]

    def test_a_detached_node_queueing_itself_is_a_no_op(self, spy_input):
        # Sem pai nao ha de quem se remover. Nao pode explodir.
        orphan = Node("Orphan")

        orphan.queue_free()
        orphan.update(spy_input)

        assert orphan.parent is None

    def test_a_subtree_carries_its_queue_into_the_new_root(self, spy_input):
        # Marcado enquanto a subarvore estava solta: o pedido tem de
        # migrar junto, senao fica preso numa lista que deixou de ser
        # raiz.
        detached = Node("Detached")
        doomed = Node("Doomed")
        detached.add_child(doomed)

        doomed.queue_free()

        root = Node("Root")
        root.add_child(detached)
        root.update(spy_input)

        assert doomed.parent is None
        assert detached.children == []


class TestQueueFreeOnAScene:
    def test_a_scene_collects_like_any_other_root(self, spy_input):
        # Scene herda de Node e nao redefine update, entao ganha a
        # coleta de raiz de graca.
        scene = Scene("Level")
        doomed = Node("Doomed")
        scene.add_child(doomed)
        scene.enter()

        doomed.queue_free()
        scene.update(spy_input)

        # Sobram as duas camadas, que a cena cria no construtor: o que
        # o teste cobra e que o no marcado saiu, e nao que a cena ficou
        # vazia.
        assert doomed not in scene.children
        assert doomed.parent is None


def build_chain(depth):
    """Uma cadeia de CountingNode, do topo para a folha."""
    chain = [CountingNode("0")]

    for i in range(1, depth):
        node = CountingNode(str(i))
        node.transform.position = Vector2D(1.0, 1.0)
        chain[-1].add_child(node)
        chain.append(node)

    return chain


class TestWorldTransformCache:
    """A transform mundial e cacheada; estes testes cuidam da validade.

    Um cache errado nao levanta excecao: ele devolve o valor de ontem,
    e o jogo desenha no lugar errado sem uma linha de erro. Por isso a
    maior parte destes testes pergunta pelo VALOR depois de mexer em
    alguma coisa, e nao pelo mecanismo.
    """

    def test_two_reads_in_a_row_return_the_same_object(self):
        node = Node("Node")

        assert node.get_world_transform() is node.get_world_transform()

    def test_writing_the_position_is_seen_by_the_next_read(self):
        node = Node("Node")
        node.get_world_transform()

        node.transform.position = Vector2D(10.0, 20.0)

        assert node.get_world_position() == Vector2D(10.0, 20.0)

    def test_writing_the_rotation_is_seen_by_the_next_read(self):
        node = Node("Node")
        node.get_world_transform()

        node.transform.rotation = 1.5

        assert node.get_world_transform().rotation == 1.5

    def test_writing_the_scale_is_seen_by_the_next_read(self):
        node = Node("Node")
        node.get_world_transform()

        node.transform.scale = Vector2D(3.0, 3.0)

        assert node.get_world_transform().scale == Vector2D(3.0, 3.0)

    def test_moving_a_parent_moves_the_cached_child(self):
        parent = Node("Parent")
        child = Node("Child")
        parent.add_child(child)
        child.get_world_position()

        parent.transform.position = Vector2D(10.0, 0.0)

        assert child.get_world_position() == Vector2D(10.0, 0.0)

    def test_the_invalidation_reaches_the_whole_subtree(self):
        # Nao basta sujar o filho direto: a sujeira desce ate o fim.
        chain = build_chain(4)
        for node in chain:
            node.get_world_position()

        chain[0].transform.position = Vector2D(100.0, 0.0)

        assert chain[-1].get_world_position() == Vector2D(103.0, 3.0)

    def test_two_writes_without_a_read_in_between_still_land(self):
        # A parada antecipada da invalidacao aposta em "no sujo tem
        # descendentes sujos". Se a aposta estiver errada, e aqui que
        # aparece: a segunda escrita nao re-suja ninguem.
        chain = build_chain(3)
        chain[-1].get_world_position()

        chain[0].transform.position = Vector2D(10.0, 0.0)
        chain[0].transform.position = Vector2D(20.0, 0.0)

        assert chain[-1].get_world_position() == Vector2D(22.0, 2.0)

    def test_a_read_in_the_middle_does_not_hide_a_later_write(self):
        chain = build_chain(3)

        chain[0].transform.position = Vector2D(10.0, 0.0)
        chain[1].get_world_position()
        chain[0].transform.position = Vector2D(20.0, 0.0)

        assert chain[-1].get_world_position() == Vector2D(22.0, 2.0)


class TestCacheAndHierarchyChanges:
    # Trocar de pai muda a transform mundial da subarvore sem que uma
    # unica transform LOCAL tenha sido escrita. E o caminho que o
    # gancho do Transform nao ve sozinho.

    def test_being_adopted_invalidates_the_new_child(self):
        parent = Node("Parent")
        parent.transform.position = Vector2D(100.0, 0.0)

        child = Node("Child")
        child.get_world_position()

        parent.add_child(child)

        assert child.get_world_position() == Vector2D(100.0, 0.0)

    def test_being_adopted_invalidates_the_whole_subtree(self):
        parent = Node("Parent")
        parent.transform.position = Vector2D(100.0, 0.0)

        chain = build_chain(3)
        chain[-1].get_world_position()

        parent.add_child(chain[0])

        assert chain[-1].get_world_position() == Vector2D(102.0, 2.0)

    def test_being_removed_falls_back_to_the_local_transform(self):
        parent = Node("Parent")
        parent.transform.position = Vector2D(100.0, 0.0)
        child = Node("Child")
        child.transform.position = Vector2D(5.0, 0.0)
        parent.add_child(child)
        child.get_world_position()

        parent.remove_child(child)

        assert child.get_world_position() == Vector2D(5.0, 0.0)

    def test_assigning_the_parent_by_hand_invalidates_too(self):
        # `parent` e publico. Montar a arvore por add_child continua
        # sendo o caminho, mas quem escrever aqui direto nao pode levar
        # um enquadramento velho de volta em silencio -- e por isso que
        # a invalidacao mora no setter, e nao dentro do add_child.
        parent = Node("Parent")
        parent.transform.position = Vector2D(100.0, 0.0)

        child = Node("Child")
        child.get_world_position()

        child.parent = parent

        assert child.get_world_position() == Vector2D(100.0, 0.0)

    def test_moving_between_parents_invalidates(self):
        first = Node("First")
        first.transform.position = Vector2D(100.0, 0.0)
        second = Node("Second")
        second.transform.position = Vector2D(200.0, 0.0)

        child = Node("Child")
        first.add_child(child)
        child.get_world_position()

        second.add_child(child)

        assert child.get_world_position() == Vector2D(200.0, 0.0)


class TestTransformOwnership:
    """`no.transform = outro` guarda uma copia, nao a instancia."""

    def test_assigning_a_transform_is_seen_by_the_next_read(self):
        node = Node("Node")
        node.get_world_transform()

        node.transform = Transform(Vector2D(7.0, 8.0))

        assert node.get_world_position() == Vector2D(7.0, 8.0)

    def test_the_assigned_transform_is_copied(self):
        node = Node("Node")
        given = Transform(Vector2D(7.0, 8.0))

        node.transform = given

        assert node.transform == given
        assert node.transform is not given

    def test_two_nodes_cannot_end_up_sharing_a_transform(self):
        # `a.transform = b.transform` ligaria os dois nos em silencio --
        # o mesmo bug que congelar o Vector2D removeu um nivel abaixo.
        a = Node("A")
        b = Node("B")

        a.transform = b.transform
        b.transform.position = Vector2D(50.0, 0.0)

        assert a.get_world_position() == Vector2D(0.0, 0.0)

    def test_the_old_transform_stops_being_listened_to(self):
        node = Node("Node")
        orphan = node.transform

        node.transform = Transform(Vector2D(1.0, 1.0))
        node.get_world_transform()
        orphan.position = Vector2D(99.0, 99.0)

        assert node.get_world_position() == Vector2D(1.0, 1.0)

    def test_writing_the_new_transform_still_invalidates(self):
        node = Node("Node")
        node.transform = Transform(Vector2D(1.0, 1.0))
        node.get_world_transform()

        node.transform.position = Vector2D(2.0, 2.0)

        assert node.get_world_position() == Vector2D(2.0, 2.0)


class TestIdleWrites:
    """Escrever o MESMO valor nao e uma mudanca.

    Sem esta guarda, o idioma mais comum que existe --
    `self.transform.rotation = 0.0` incondicional num on_update --
    sujaria a subarvore inteira em todo frame e o cache nunca
    acertaria.
    """

    def test_rewriting_the_same_value_keeps_the_cache(self):
        node = Node("Node")
        node.transform.rotation = 0.5
        cached = node.get_world_transform()

        node.transform.rotation = 0.5

        assert node.get_world_transform() is cached

    def test_rewriting_the_same_position_keeps_the_cache(self):
        node = Node("Node")
        node.transform.position = Vector2D(3.0, 4.0)
        cached = node.get_world_transform()

        node.transform.position = Vector2D(3.0, 4.0)

        assert node.get_world_transform() is cached

    def test_an_equal_but_distinct_vector_still_counts_as_the_same(self):
        # Por valor, e nao por identidade: dois Vector2D iguais sao o
        # mesmo valor, e o Vector2D e imutavel, entao nao ha diferenca
        # que possa aparecer depois.
        node = Node("Node")
        node.transform.position = Vector2D(3.0, 4.0)
        cached = node.get_world_transform()

        node.transform.position = Vector2D(3.0, 4.0)

        assert node.get_world_transform() is cached

    def test_a_real_change_after_an_idle_write_still_lands(self):
        node = Node("Node")
        node.get_world_transform()

        node.transform.rotation = 0.0
        node.transform.rotation = 1.0

        assert node.get_world_transform().rotation == 1.0


class TestWritingToTheReturnedWorldTransform:
    """A leitura devolve o proprio objeto cacheado, sem copia.

    Antes do cache, escrever na transform mundial devolvida era
    silenciosamente ignorado -- ela era descartavel. Sem cuidado
    passaria a CORROMPER o cache, que e pior. O gancho mantem a
    semantica antiga: a escrita apenas suja o no, e a proxima leitura
    recalcula do local e do pai.
    """

    def test_writing_to_it_does_not_corrupt_the_next_read(self):
        node = Node("Node")
        node.transform.position = Vector2D(5.0, 5.0)

        world = node.get_world_transform()
        world.position = Vector2D(99.0, 99.0)

        assert node.get_world_position() == Vector2D(5.0, 5.0)

    def test_writing_to_it_does_not_reach_the_children(self):
        parent = Node("Parent")
        child = Node("Child")
        parent.add_child(child)

        world = parent.get_world_transform()
        world.position = Vector2D(99.0, 99.0)

        assert child.get_world_position() == Vector2D(0.0, 0.0)


class TestCacheAgreesWithAFreshComputation:
    def test_a_scripted_sequence_never_disagrees(self):
        # Oraculo: a implementacao sem cache. Um cache so pode ser
        # testado contra a resposta que ele deveria ter dado.
        root = Node("root")
        a = Node("a")
        b = Node("b")
        c = Node("c")

        root.add_child(a)
        a.add_child(b)
        b.add_child(c)

        nodes = (root, a, b, c)

        def check():
            for node in nodes:
                assert node.get_world_transform() == uncached_world_transform(
                    node
                )

        check()

        steps = [
            lambda: setattr(root.transform, "position", Vector2D(10.0, 5.0)),
            lambda: setattr(a.transform, "rotation", math.pi / 3.0),
            lambda: setattr(b.transform, "scale", Vector2D(2.0, 2.0)),
            lambda: setattr(c.transform, "position", Vector2D(3.0, -1.0)),
            # Uma leitura no meio, para que a proxima escrita tenha um
            # cache quente para invalidar.
            lambda: c.get_world_position(),
            lambda: setattr(root.transform, "rotation", 0.25),
            # Reparenting: sem escrita local nenhuma.
            lambda: root.add_child(c),
            lambda: setattr(a.transform, "position", Vector2D(-4.0, 8.0)),
            lambda: b.remove_child(c) if c.parent is b else None,
            lambda: b.add_child(c),
            # Escrita ociosa: nao pode mudar resposta nenhuma.
            lambda: setattr(root.transform, "rotation", 0.25),
            # Troca da transform local inteira.
            lambda: setattr(a, "transform", Transform(Vector2D(1.0, 2.0))),
        ]

        for step in steps:
            step()
            check()


class TestCacheCost:
    """O ganho, medido em resolucoes da transform mundial por no.

    Sem estes testes o cache continuaria correto e poderia parar de
    acertar sem que nenhum teste de valor percebesse.
    """

    def test_a_hit_does_not_touch_the_parent(self):
        # O ponto do passo inteiro: acerto O(1), que nao sobe a cadeia.
        chain = build_chain(4)
        chain[-1].get_world_transform()
        for node in chain:
            node.resolutions = 0

        chain[-1].get_world_transform()

        assert [node.resolutions for node in chain] == [0, 0, 0, 1]

    def test_a_cold_read_climbs_each_level_once(self):
        chain = build_chain(4)

        chain[-1].get_world_transform()

        assert [node.resolutions for node in chain] == [1, 1, 1, 1]

    def test_a_still_frame_costs_one_resolution_per_node(self):
        # O ideal que o README persegue: 6 nos encadeados, 6 subidas.
        # Um frame parado le cada no uma vez e nao sobe cadeia nenhuma.
        chain = build_chain(6)
        for node in chain:
            node.get_world_transform()
        for node in chain:
            node.resolutions = 0

        for node in chain:
            node.get_world_transform()

        assert sum(node.resolutions for node in chain) == 6

    def test_moving_the_root_costs_one_extra_resolution_per_level(self):
        chain = build_chain(6)
        for node in chain:
            node.get_world_transform()
        for node in chain:
            node.resolutions = 0

        chain[0].transform.position = Vector2D(1.0, 0.0)
        for node in chain:
            node.get_world_transform()

        # Cada no resolve a propria (6) e o pai de cada um e consultado
        # uma vez no miss (5). O antigo custava 21.
        assert sum(node.resolutions for node in chain) == 11
