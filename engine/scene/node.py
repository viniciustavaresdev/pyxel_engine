from __future__ import annotations

from engine.math.transform import Transform
from engine.math.vector2d import Vector2D
from engine.ports.input import Input
from engine.ports.renderer import Renderer


class Node:
    def __init__(self, name: str | None = None) -> None:
        self.name = name

        # Cache da transform mundial. None quer dizer SUJO, e nao
        # "zerado": um Transform identidade e um valor legitimo, e usar
        # um par (valor, bandeira) daria duas fontes de verdade que
        # podem discordar.
        #
        # Vem primeiro porque as duas linhas seguintes ja invalidam, e
        # invalidar precisa encontrar o cache e a lista de filhos de pe.
        self._world_transform: Transform | None = None
        self.children: list[Node] = []

        self._parent: Node | None = None

        # Atribuido pelo campo, e nao pela property: o setter copia e
        # invalida, e nem a copia nem a invalidacao fazem sentido antes
        # de o no existir. Depois disto o caminho e sempre a property.
        self._transform = Transform()
        self._transform._on_change = self._invalidate_world_transform

        # Dois gates separados de proposito: um no pausado que continua
        # desenhado (inimigo congelado) e coisa diferente de um no
        # invisivel que continua rodando (spawner, gatilho de area).
        self.active = True
        self.visible = True

        self._inside_tree = False
        self._queued_for_removal = False

        # So a lista da RAIZ e usada; nos do meio carregam a propria
        # vazia. A alternativa -- criar sob demanda -- economizaria uma
        # lista por no e custaria um `if` em todo caminho que a toca.
        self._pending_removals: list[Node] = []

    # Hierarchy link
    @property
    def parent(self) -> Node | None:
        return self._parent

    @parent.setter
    def parent(self, parent: Node | None) -> None:
        """Trocar de pai muda a transform mundial da subarvore inteira.

        E o unico caminho de invalidacao que o gancho do Transform nao
        enxerga: nenhuma transform LOCAL foi escrita, e mesmo assim
        todo mundo abaixo daqui passou a responder a outro referencial.

        Interceptar aqui, e nao dentro de add_child/remove_child, e o
        que fecha a conta: com o gancho do Transform de um lado e este
        setter do outro, TODA mudanca que pode alterar uma transform
        mundial passa por um dos dois. Nao sobra caminho por onde o
        cache envelheca em silencio.
        """
        self._parent = parent

        self._invalidate_world_transform()

    # Local transform
    @property
    def transform(self) -> Transform:
        """O sistema de coordenadas LOCAL do no.

        Escrever nos campos dele -- `no.transform.rotation += x` -- e a
        ergonomia esperada, e continua sendo: o que mudou e que agora a
        escrita avisa o no, que joga fora o cache da propria subarvore.
        """
        return self._transform

    @transform.setter
    def transform(self, transform: Transform) -> None:
        """Troca a transform local inteira de uma vez.

        Guarda uma COPIA, e nao a instancia recebida. Sao dois motivos,
        e o segundo e o que decide:

        - o no precisa do proprio gancho de invalidacao no transform
          que guarda, e pendura-lo no objeto de quem chamou mexeria num
          objeto que nao e dele;
        - `a.transform = b.transform` ligaria os dois nos em silencio,
          exatamente o bug que congelar o Vector2D removeu um nivel
          abaixo. Aqui o mesmo remedio: `no.transform is o_que_passei`
          e falso, de proposito.
        """
        self._transform._on_change = None

        self._transform = transform.copy()
        self._transform._on_change = self._invalidate_world_transform

        self._invalidate_world_transform()

    # Hierarchy
    def add_child(self, child: Node) -> None:
        if child is self:
            raise ValueError("A node cannot be its own child.")

        if child.is_ancestor_of(self):
            raise ValueError("Cannot create a cycle in the scene graph.")

        if child.parent is not None:
            child.parent.remove_child(child)

        # O setter de `parent` invalida a subarvore do filho.
        child.parent = self
        self.children.append(child)

        # A fila mora na raiz, e o filho acabou de trocar de raiz.
        # Sem levar os pedidos dele junto, um no marcado enquanto a
        # subarvore estava solta ficaria preso numa lista que nao e
        # mais raiz de ninguem -- e nunca seria coletado.
        if child._pending_removals:
            root = self.get_root()
            root._pending_removals.extend(child._pending_removals)
            child._pending_removals.clear()

        # Se esta arvore ja esta viva, o filho tem de acordar agora --
        # senao um no criado durante o jogo nunca receberia on_enter.
        # Numa arvore ainda fria ele entra junto com todos no enter().
        if self._inside_tree:
            child.enter()

    def remove_child(self, child: Node) -> None:
        if child not in self.children:
            return

        if child._inside_tree:
            child.exit()

        self.children.remove(child)

        # O setter de `parent` invalida a subarvore do filho, que
        # passou a responder pela transform local dela.
        child.parent = None

        # Zera a marca: o no pode ser readotado por outro pai, e nao
        # deve morrer de novo no primeiro frame la.
        child._queued_for_removal = False

    def queue_free(self) -> None:
        """Marca o no para sair da arvore no fim do frame.

        Seguro de chamar de dentro do proprio on_update: a coleta
        acontece depois que a travessia inteira terminou, entao o no
        vive o frame por completo antes de sair.

        O pedido e registrado na RAIZ da arvore, nao no pai. A
        diferenca importa: uma fila por pai so seria esvaziada no
        update daquele pai, e um pai com `active = False` retorna cedo
        -- entao desativar um ramo (pausar um inimigo, congelar uma
        fase) congelava junto todas as remocoes pendentes dele, e o no
        marcado continuava na arvore e continuava sendo desenhado,
        porque render nao olha `active`.

        Num no solto, sem pai, e um no-op: nao ha de quem se remover.
        """
        if self._queued_for_removal:
            return

        self._queued_for_removal = True

        self.get_root()._pending_removals.append(self)

    @property
    def is_queued_for_removal(self) -> bool:
        # Publico porque o codigo de jogo precisa: mirar em um alvo que
        # ja pediu para morrer e desperdicio na melhor das hipoteses.
        return self._queued_for_removal

    @property
    def is_inside_tree(self) -> bool:
        return self._inside_tree

    def get_root(self) -> Node:
        """O no mais alto da arvore -- ele proprio, se nao tiver pai."""
        node = self

        while node.parent is not None:
            node = node.parent

        return node

    # Lifecycle
    def enter(self) -> None:
        self._inside_tree = True

        self.on_enter()

        for child in tuple(self.children):
            child.enter()

    def on_enter(self) -> None:
        pass

    def exit(self) -> None:
        for child in tuple(self.children):
            child.exit()

        self.on_exit()

        self._inside_tree = False

    def on_exit(self) -> None:
        pass

    # Update
    def update(self, input: Input) -> None:
        """Um update e UM FRAME. Nao ha dt, e isso e uma decisao.

        Quem e dono do laco e a porta `Application` -- `pyxel.run`
        chama isto a uma cadencia fixa, e medir o tempo aqui dentro
        seria o nucleo refazendo uma conta que a infraestrutura ja fez.
        A variancia que sobrava daquela medicao era o unico motivo de
        existir um teto de dt; sem medir, a classe inteira de bug (um
        breakpoint virando um salto que atravessa paredes) deixa de
        existir em vez de ser contida.

        A contrapartida esta no codigo de jogo: velocidade passa a ser
        POR FRAME, e a taxa do `ApplicationConfig` passa a governar a
        fisica. Trocar 60 por 30 ali deixa tudo duas vezes mais lento.
        """
        if not self.active:
            return

        self.on_update(input)

        # tuple(): on_update pode ter adicionado ou removido filhos.
        # Iterar a lista viva faria o traversal pular nos em silencio.
        # O snapshot tambem define a regra: quem nasceu neste frame so
        # roda no proximo.
        for child in tuple(self.children):
            # Pode ter sido removido por um irmao que ja rodou.
            if child.parent is self:
                child.update(input)

        # So a raiz coleta, e so depois de a travessia inteira acabar:
        # um instante unico e deterministico de remocao por frame, em
        # vez de um por pai espalhado pelo meio do percurso.
        if self.parent is None:
            self._flush_pending_removals()

    def on_update(self, input: Input) -> None:
        pass

    def _flush_pending_removals(self) -> None:
        # Uma passada so. O que for marcado durante a coleta -- de
        # dentro de um on_exit, tipicamente -- espera o proximo frame,
        # pela mesma regra que ja vale para quem nasce no meio do
        # frame.
        pending = tuple(self._pending_removals)

        self._pending_removals.clear()

        for node in pending:
            # A marca pode ter sido desfeita no intervalo: remove_child
            # a limpa, entao um no ja retirado ou readotado por outro
            # pai nao pode ser arrancado da arvore nova.
            if node._queued_for_removal and node.parent is not None:
                node.parent.remove_child(node)

    # Render
    def render(self, renderer: Renderer) -> None:
        if not self.visible:
            return

        self.on_render(renderer)

        for child in tuple(self.children):
            child.render(renderer)

    def on_render(self, renderer: Renderer) -> None:
        pass

    # World transform
    def get_world_transform(self) -> Transform:
        """A transform acumulada da raiz ate aqui.

        Cacheada. O acerto e O(1) e NAO toca no pai -- e o que faz o
        custo de um frame parado deixar de crescer com a profundidade
        da arvore.

        A pergunta que o cache tem de responder e "fiquei velho?", e
        ela nao e feita na leitura: e respondida na escrita, por quem
        escreveu. Ver `_invalidate_world_transform`.
        """
        cached = self._world_transform

        if cached is None:
            # `_parent`, e nao a property: e o caminho quente, e o
            # getter so existe para o setter poder invalidar.
            parent = self._parent

            if parent is None:
                cached = self._transform.copy()
            else:
                cached = parent.get_world_transform().compose(self._transform)

            self._world_transform = cached

            # O valor devolvido e o proprio objeto cacheado, e nao uma
            # copia: copiar em toda leitura devolveria ao caminho de
            # render uma alocacao por no por frame, que e metade do que
            # este passo veio economizar.
            #
            # O gancho e o que torna isso seguro. Antes do cache,
            # escrever na transform mundial devolvida era silenciosamente
            # ignorado -- ela era um objeto descartavel. Sem o gancho
            # passaria a corromper o cache em silencio, que e pior.
            # Com ele, a escrita apenas suja o no: a proxima leitura
            # recalcula do local e do pai, e a escrita continua sendo
            # ignorada. Mesma semantica de antes, sem copia.
            cached._on_change = self._invalidate_world_transform

        return cached

    def _invalidate_world_transform(self) -> None:
        """Joga fora o cache deste no e o da subarvore inteira.

        Empurra a sujeira para baixo em vez de deixar cada leitura
        perguntar ao pai: e a diferenca entre um acerto O(1) e um
        acerto O(profundidade).

        A parada antecipada nao e uma otimizacao solta, ela se apoia em
        um invariante: SE UM NO ESTA SUJO, TODOS OS DESCENDENTES DELE
        ESTAO. Vale porque limpar um no exige subir a cadeia inteira e
        limpar os ancestrais junto -- entao nunca ha filho limpo sob
        pai sujo. Com ele, escrever varias vezes na mesma transform
        entre dois desenhos custa uma travessia so.
        """
        if self._world_transform is None:
            return

        self._world_transform = None

        for child in self.children:
            child._invalidate_world_transform()

    def get_world_position(self) -> Vector2D:
        return self.get_world_transform().position

    # Hierarchy helpers
    def is_ancestor_of(self, node: Node) -> bool:
        current = node.parent

        while current is not None:
            if current is self:
                return True

            current = current.parent

        return False
