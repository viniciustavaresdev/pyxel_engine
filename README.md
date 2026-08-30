# pyxel-engine

Engine 2D de *scene graph* em Python, com [Pyxel](https://github.com/kitao/pyxel)
como backend — e com o núcleo isolado dele por portas.

A regra que organiza o projeto inteiro cabe em uma linha: **nenhum
`import pyxel` fora de `engine/adapters/`.** O código de jogo fala com
abstrações (`Renderer`, `Input`, `Application`, `TimeProvider`), nunca com o
backend. A consequência prática é que a suíte de testes roda sem abrir janela
nenhuma, e trocar de backend passa a ser escrever outro adaptador em vez de
caçar constantes espalhadas pelas cenas.

---

## Rodando

```bash
python -m venv venv
venv\Scripts\activate          # Windows
pip install -e ".[dev]"

python main.py                 # a demo
pytest                         # 432 testes, sem janela
```

Verificação (as três precisam passar limpas):

```bash
ruff check .                   # lint + ordem de imports
black --check .                # formatação
mypy                           # --strict em engine/ e tests/
```

---

## As camadas

```
        ┌──────────────────────────────────────────────┐
        │  jogo (main.py, games/)                      │
        │  from engine import Node, Vector2D, ...      │
        └────────────────────┬─────────────────────────┘
                             │
        ┌────────────────────▼─────────────────────────┐
        │  engine/math  scene  runtime  input          │
        │  valores, a árvore, o laço de frame          │
        └────────────────────┬─────────────────────────┘
                             │  depende só de abstrações
        ┌────────────────────▼─────────────────────────┐
        │  engine/ports/                               │
        │  Renderer  Input  Application  TimeProvider  │
        └────────────────────▲─────────────────────────┘
                             │  implementa
        ┌────────────────────┴─────────────────────────┐
        │  engine/adapters/pyxel/  stdlib/             │
        │  ← o único lugar que conhece o Pyxel         │
        └──────────────────────────────────────────────┘
```

A seta se inverte na fronteira das portas: o núcleo não desce até a
infraestrutura, é a infraestrutura que sobe para satisfazer o contrato. É o que
mantém a dependência apontando sempre para dentro.

---

## Conceitos

### Node — a árvore

Tudo é `Node`. Um nó tem `transform`, filhos, e três ganchos:
`on_enter` / `on_update` / `on_render`. A travessia é feita sobre um snapshot
(`tuple(self.children)`), o que define uma regra útil: um nó criado durante o
frame só roda no frame seguinte, e remover um irmão no meio do update não faz o
traversal pular ninguém.

`queue_free()` marca para remoção adiada — seguro de chamar de dentro do próprio
`on_update`, porque o nó termina o frame antes de sair da árvore. O pedido é
registrado na **raiz**, não no pai, e a coleta acontece uma vez por frame depois
que a travessia inteira terminou: um instante único e determinístico de remoção,
em vez de um por pai espalhado pelo meio do percurso.

Dois portões separados de propósito: `active` (roda) e `visible` (desenha). Um
inimigo congelado que continua na tela e um spawner invisível que continua
funcionando são coisas diferentes.

**`get_world_transform()` é cacheada.** O acerto é O(1) e não toca no pai — é o
que faz o custo de um frame parado deixar de crescer com a profundidade da
árvore. A pergunta "fiquei velho?" não é feita na leitura: é respondida na
escrita, por quem escreveu, e a sujeira desce pela subárvore.

Só há dois jeitos de uma transform mundial mudar, e cada um tem seu
interceptador:

| o que mudou | quem avisa |
|---|---|
| a transform **local** (`position`, `rotation`, `scale`) | o `_on_change` do `Transform` |
| o **pai** — nenhuma escrita local, e mesmo assim outro referencial | o setter de `Node.parent` |

A invalidação mora no setter de `parent`, e não dentro de `add_child`, de
propósito: é o que fecha a conta. Com os dois interceptadores não sobra caminho
por onde o cache envelheça em silêncio — nem `no.parent = outro` escrito na mão.

A parada antecipada da invalidação se apoia num invariante que vale a pena
enunciar: **se um nó está sujo, todos os descendentes dele estão.** Vale porque
limpar um nó exige subir a cadeia e limpar os ancestrais junto, então nunca há
filho limpo sob pai sujo. Com ele, escrever cinco vezes na mesma transform entre
dois desenhos custa uma travessia só.

### Transform — coordenadas, e só

`position`, `rotation` (radianos), `scale`. `compose()` aplica a transform local
por cima da do pai na ordem **escala → rotação → translação**. Guarda a
decomposição em vez de uma matriz: é o mesmo compromisso do `lossyScale` da
Unity — exato enquanto a escala for uniforme, e sem representar cisalhamento.
Para pixel art isso não aparece, e evita carregar uma classe de matriz inteira.

`Transform` não conhece pixels. Não tem tamanho, não tem pivô, não sabe o que é
um sprite.

Ele é **mutável**, mas os valores que guarda não: `Vector2D` é congelado. A
combinação é deliberada — `no.transform.rotation += x` continua sendo a ergonomia
esperada de um nó de jogo, enquanto `position.x += 1`, que acontecia fundo demais
para qualquer um notar, deixou de existir. Toda alteração passa agora por uma
atribuição em `Transform`, e uma atribuição é interceptável.

**E é interceptada.** Cada campo é uma *property* que avisa um `_on_change`
opcional. É o gancho de que o cache de transform mundial do `Node` depende — e
o motivo pelo qual congelar o `Vector2D` (passo 6) tinha de vir antes.

Duas decisões dentro do gancho, ambas medidas:

- **Properties, e não `__setattr__`.** Um `__setattr__` intercepta também os
  writes do próprio construtor, e `compose()` constrói um `Transform` por nó por
  nível no caminho de render. Medido: construir um `Transform` passa de 102 ns
  para **2135 ns**, 20x, pago exatamente onde o cache ainda não ajudou. Com
  properties o construtor escreve nos slots privados e não passa por gancho
  nenhum. O preço é `__init__`, `__eq__` e `__repr__` escritos à mão, que o
  `dataclass` dava de graça.
- **Escrever o mesmo valor não é uma mudança.** `self.transform.rotation = 0.0`
  incondicional num `on_update` é o idioma mais comum que existe; sem a guarda
  de igualdade ele sujaria a subárvore inteira todo frame e o cache nunca
  acertaria. Com ela, esse caso custa o mesmo que não escrever nada.

### Anchor + VisualNode — onde o desenho se pendura na origem

A rotação **sempre** acontece na origem do nó. O que decide se um objeto gira
pelo centro ou pelo canto não é a matemática, é onde a origem cai dentro do
desenho — e isso é o `Anchor`, um valor normalizado (`0..1`) que vive em
`VisualNode`, o único nó que tem `size`.

```python
class Player(VisualNode):
    def __init__(self):
        super().__init__(size=Vector2D(8.0, 8.0))   # Anchor.CENTER é o default
```

Com `Anchor.CENTER`, três coisas passam a valer ao mesmo tempo e de graça: o nó
gira em torno do próprio centro, um filho pendurado nele orbita esse centro, e a
câmera presa a ele enquadra esse centro.

| Anchor | uso típico |
|---|---|
| `CENTER` | naves, projéteis, qualquer coisa que gire |
| `BOTTOM_CENTER` | personagens — a origem nos pés faz o sprite encostar no chão sozinho, e uma arte mais alta cresce para cima em vez de afundar |
| `TOP_LEFT` | tiles e marcos de grade, que precisam começar exatamente na coordenada que nomeiam |

Para desenhar:

- `get_world_bounds() -> Rect` — **o que um `on_render` deve chamar.** Canto e
  tamanho de uma vez, resolvendo a transform mundial uma vez só. O idioma
  anterior (`draw_rect(get_world_top_left(), get_world_size(), cor)`) parecia
  barato e custava três subidas da hierarquia por nó.
- `get_world_center()` — exato para qualquer anchor e rotação. É o que os
  backends que giram em torno do centro pedem.
- `get_world_top_left()` — para primitivas que não giram (`draw_rect`, texto)
  quando só o canto interessa.

Nos três, o centro respeita a rotação da hierarquia inteira, mas a *orientação*
da caixa se perde: um retângulo alinhado aos eixos não tem como expressá-la. A
perda é assumida, não é bug escondido.

### Rect — a mesma peça vista de dois lados

`Rect` era só a região de um sprite dentro do atlas. Ganhou `center`,
`from_center_size`, `contains` e `intersects`, e com isso passou a ser também a
caixa que `get_world_bounds()` devolve — o que entrega colisão AABB sem uma
linha nova:

```python
if player.get_world_bounds().intersects(enemy.get_world_bounds()):
    ...
```

Duas decisões que valem estar escritas, porque são as que um AABB erra:

- **Intervalo semiaberto.** A borda de cima e a da esquerda pertencem à caixa,
  as de baixo e da direita não. É o que faz caixas encostadas ladrilharem o
  plano sem que a linha compartilhada pertença às duas — num grid de tiles, um
  ponto sobre a divisa cai em exatamente um tile. Encostar não é sobrepor: um
  jogador parado exatamente sobre o chão não está afundado nele.
- **Área zero não colide com nada**, nem estando bem no meio da outra caixa. A
  definição é "existe ponto que as duas contêm", e uma caixa vazia não contém
  ponto nenhum. Um nó sem tamanho é um marco de spawn, não um corpo.

Largura negativa continua sendo o idioma de espelhamento do backend. Como o
sinal não quer dizer nada numa pergunta de colisão — e `0 <= x < -8` é falso
para todo `x`, em silêncio — `contains` e `intersects` normalizam por dentro.
`normalized()` é público e devolve `self` quando já está normalizado, então o
caminho comum não aloca.

### Camera — um nó como qualquer outro

Pendure a câmera como filha do jogador e ela o segue pela transform hierárquica,
sem uma linha de código de *follow*. A posição mundial da câmera é o **centro**
da tela, não o canto — inverte o sinal em relação ao backend, mas evita que todo
jogo repita a mesma subtração de meia tela.

O enquadramento é aplicado na raiz, pela `Scene`, e não no `on_render` de algum
nó: se dependesse da ordem de visita, bastaria alguém reordenar os filhos para
metade da cena desenhar com o enquadramento errado.

### Camadas — `world` e `ui`, e quem decide o espaço

Toda `Scene` nasce com duas subárvores. `world` desenha enquadrada pela câmera;
`ui` desenha em coordenadas de tela, **depois** do mundo inteiro:

```python
self.world.add_child(player)
self.ui.add_child(Hud("Hud", player))     # a ordem aqui não importa
```

O que isso substituiu: um HUD que chamava `reset_camera()` dentro do próprio
`on_render` e só estava correto enquanto fosse o último filho da cena. Era estado
global do renderer alterado no meio da travessia, com uma dependência de ordem
que ninguém declarava — e que qualquer `add_child` a mais quebrava em silêncio.
Agora a passada de UI é da cena, que já era quem decidia o enquadramento.

Três coisas que a implementação fixa:

- **As camadas são `Node`s comuns**, filhas da cena. Ganham `update`,
  `enter`/`exit` e a fila de remoção pelos caminhos que já existiam, sem uma
  linha nova. Camada aqui é ordem e espaço de desenho, e nada mais.
- **Só leitura.** Trocar `scene.ui` por outro nó deixaria a camada antiga
  pendurada na cena, ainda desenhando, e o `render` procurando a nova. O mypy
  recusa a atribuição e o runtime também — a proteção não depende de alguém
  rodar o checador.
- **Camada de UI vazia não custa chamada nenhuma.** Uma cena que não usa UI tem
  exatamente o mesmo tráfego de renderer de antes das camadas, e o `reset_camera`
  aparece no frame por um motivo visível, em vez de por cerimônia.

Pendurar direto na cena continua valendo e continua caindo em espaço de mundo: a
UI é a única exceção, e ela é declarada. O que `world` acrescenta é poder tratar
o mundo como uma coisa só — e é aí que um menu de pausa vira uma linha:

```python
scene.world.active = False      # o mundo congela; a UI segue viva
scene.world.visible = False     # o mundo some; o menu fica
```

São os dois portões do `Node` (`active` e `visible`) aplicados a uma camada
inteira. `z_index` dentro de uma camada continua fora, até um jogo pedir.

### Clock — dt com teto

`max_delta_time` de 0,1 s por padrão: um breakpoint ou um travamento do sistema
não pode virar um dt gigante que atravessa o jogador pela parede. `reset()`
re-ancora o relógio sem zerar o tempo acumulado, para que retomar de uma pausa
não reinicie o tempo de jogo.

### Input — três perguntas, não uma

`is_pressed` (segurar para andar), `is_just_pressed` (o instante do pulo) e
`is_just_released` (soltar um tiro carregado). Colapsar isso em uma só faria o
pulo disparar em todo frame com a tecla baixa.

O enum `Key` é próprio, e existe um teste que falha se uma tecla nova não for
mapeada no adaptador — transformando um `KeyError` em pleno jogo numa falha de
build.

### ActionMap — de teclas para intenções

`is_pressed(Key.LEFT) or is_pressed(Key.A)`, repetido em quatro linhas, é código
de jogo enumerando teclas onde queria nomear uma intenção — e a lista se repete
em todo lugar que precisa dela. O `ActionMap` guarda essa lista uma vez:

```python
class Action(Enum):          # o vocabulário é do JOGO, não da engine
    MOVE_LEFT = auto()
    ...

actions = ActionMap({Action.MOVE_LEFT: {Key.LEFT, Key.A}, ...})

direction = actions.get_vector(
    Action.MOVE_LEFT, Action.MOVE_RIGHT, Action.MOVE_UP, Action.MOVE_DOWN, input
)
```

**Genérico no tipo da ação, e não fixado em `str`.** `Key` a engine precisa
possuir — é o que mantém o `import pyxel` fora do código de jogo —, mas "pular" e
"girar" são vocabulário de quem está sendo escrito, e uma engine que enumerasse
ações estaria adivinhando o jogo. Com `ActionMap[Action]` e o `Enum` do jogo, um
nome errado é erro de mypy; quem preferir strings usa `ActionMap[str]` e paga a
diferença em `KeyError`.

O mapa **não guarda o input**: recebe um a cada pergunta. Sem estado próprio além
das amarrações, o mesmo mapa serve à árvore inteira e continua respondendo pelo
frame que o laço está passando, sem nenhuma sincronia para manter.

Três decisões que valem estar escritas:

- **Ação não amarrada levanta**, em vez de devolver "não pressionada". É o modo
  de falha mais caro que este mapa poderia ter: o jogo roda, o botão não faz
  nada, e não há uma linha de erro para procurar. Amarrar ao conjunto vazio é
  outra coisa — um controle desligado de propósito — e responde `False`.
- **`is_just_pressed` é da AÇÃO, não da tecla.** Com ESPAÇO segurado, tocar Z
  não dispara um segundo pulo com o jogador já no ar: a ação já estava valendo, o
  que mudou foi só por qual tecla. E é respondido sem memória de frame — uma
  tecla baixa que *não* desceu agora já estava baixa antes. `is_just_released` é
  o espelho: soltar ESPAÇO com o Z ainda baixo não solta o tiro carregado.
- **`get_vector` normaliza.** É para onde foi a normalização manual de diagonal
  do `Player`; sem ela a diagonal anda 41% mais rápido que a reta, e todo jogo
  redescobre isso sozinho. `get_axis` dá o eixo cru: as duas direções ao mesmo
  tempo se anulam, porque a alternativa ("a última vence") exige memória, e um
  eixo com memória é um eixo que discorda do teclado depois de uma pausa.

`bind()` **substitui** em vez de acumular: é a operação de uma tela de
remapeamento, e acumular deixaria a tecla antiga respondendo junto com a nova —
exatamente o que o jogador pediu para não acontecer.

---

## Um detalhe do backend que vale registrar

O `pyxel.blt` recebe o **canto** da região não girada, mas gira e escala em
torno do **centro** dela — mantendo o centro fixo em `(x + w/2, y + h/2)`, com
`w,h` *sem* a escala aplicada. Verificado desenhando em uma `pyxel.Image` fora
da tela: girar 90° ou dobrar a escala muda a caixa desenhada e não mexe no
centro.

Por isso a porta `Renderer.draw_sprite` recebe `center` e não `position`: é o
único método que gira, e um desenho que gira precisa dizer em torno de quê. O
adaptador faz a conversão. `draw_rect`, que não gira, continua falando em canto.

---

## Estrutura de pastas

```
engine/
├── math/            valor puro: sem tempo, sem árvore, sem backend
│   └── vector2d.py  rect.py  anchor.py  transform.py
├── scene/           a árvore e quem vive nela
│   └── node.py  visual_node.py  scene.py  scene_manager.py  camera.py
├── runtime/         o laço de frame e a composição do jogo
│   └── engine.py  game.py  clock.py  application_config.py
├── input/           vocabulário de entrada
│   └── key.py  action_map.py
├── ports/           o que a engine exige do mundo
│   └── renderer.py  input.py  application.py  time_provider.py
└── adapters/        quem cumpre a exigência
    ├── pyxel/       pyxel_renderer.py  pyxel_input.py  ...
    └── stdlib/      performance_time_provider.py
```

`tests/` espelha essa árvore: `tests/math/`, `tests/scene/`, `tests/runtime/`,
`tests/input/`, `tests/ports/`, `tests/adapters/`.

O critério: cada pasta responde **o que não entra aqui**. Em `math/` não entra
nada que conheça tempo ou árvore; em `scene/` nada que conheça o laço de frame;
em `ports/` nenhuma implementação. Uma pasta que aceita qualquer arquivo — o
antigo `core/`, que acumulou quatro naturezas diferentes — parou de organizar e
virou só o lugar onde as coisas estão.

Duas coisas que a reorganização corrigiu de passagem: `transform.py` estava fora
do `math/` sendo valor puro como os outros três, e `infrastructure/` misturava
dois eixos de nomeação (`pyxel/` pelo backend, `time/` pela porta — virou
`adapters/stdlib/`).

### A superfície pública

`engine/__init__.py` reexporta os 19 nomes que um jogo realmente usa. O que está
lá é contrato; o resto é detalhe interno, livre para mudar de módulo sem aviso.

```python
from engine import Node, VisualNode, Scene, Camera, Vector2D, Anchor, Key
```

**Os adaptadores ficam de fora de propósito.** Reexportar `PyxelRenderer` ali
faria `import engine` executar `import pyxel`, e a promessa de que o núcleo não
conhece o backend passaria a valer por acidente — até o dia em que alguém rodasse
a suíte numa máquina sem o Pyxel instalado. Deixando-os fora, a fronteira aparece
na própria forma de importar:

```python
from engine import Node, Vector2D                                  # núcleo
from engine.adapters.pyxel.pyxel_renderer import PyxelRenderer     # backend
```

A linha mais longa é a que amarra o jogo a um backend. É bom que doa um pouco.

Três testes em `tests/test_public_api.py` trancam isso, e o terceiro é o que
impede os outros dois de virarem vácuos: ele exige que importar um adaptador
**de fato** carregue o Pyxel. Sem ele, "o Pyxel não foi carregado" passaria a ser
verdade por nunca ninguém carregá-lo. A checagem roda em subprocesso, porque
`sys.modules` é do processo inteiro e responderia sobre a ordem dos testes.

---


## Estado atual e próximos passos

A separação núcleo/backend está sólida, os dois bugs de ciclo de vida estão
fechados, as duas decisões de baixo nível foram tomadas, a engine cabe no
orçamento de frame e o projeto está sob controle de versão. **Os dez passos da
sequência estão feitos** — os dois últimos, mapa de ações e camadas de render,
são os que se sentem escrevendo jogo em vez de engine.

O que resta não é sequência, é lista de espera: resposta a colisão, `z_index`,
`find_child`, o tamanho de tela que vive em dois lugares, e o acabamento. Cada um
entra quando um jogo pedir — e um jogo é o que falta para saber qual pede
primeiro.

### Bugs confirmados

**~~`queue_free()` numa subárvore inativa nunca é coletado.~~ Corrigido.** A fila
era *por pai* e só esvaziava dentro de `Node.update()`, que retorna cedo quando
`active` é falso — então `leaf.queue_free()` seguido de `branch.active = False`
deixava o nó na árvore indefinidamente, e ele continuava sendo desenhado, porque
`render` não olha `active`.

A fila passou para a raiz (`Node.get_root()`), esvaziada uma vez por frame após
a travessia. Três arestas que o novo desenho precisou fechar, cada uma com teste:

- **Idempotência** — `queue_free()` duas vezes enfileira uma vez só.
- **Readoção antes da coleta** — um nó marcado, retirado na mão e pendurado em
  outra árvore não pode ser arrancado da árvore nova, que nunca pediu nada. A
  guarda é o próprio `_queued_for_removal`, que o `remove_child` já zerava.
- **Subárvore montada solta** — um nó marcado antes de a subárvore ser anexada
  teria o pedido preso numa lista que deixou de ser raiz. O `add_child` migra a
  fila do filho para a raiz nova.

**~~`Scene.camera` continua apontando para uma câmera removida.~~ Corrigido.**
Era referência forte que ninguém limpava: com a câmera fora da árvore,
`get_view_offset()` passava a usar a transform *local* dela — `parent` virou
`None` — e o enquadramento saltava para outro canto do mundo sem erro nenhum.

Virou `property` que devolve `None` quando a câmera não está mais pendurada na
cena, caindo no caminho de "sem câmera" que já existia. O predicado exigiu duas
tentativas:

- `is_inside_tree` **não serve**: a cena precisa poder ser montada e desenhada
  antes do `enter()`, e nesse intervalo a flag é falsa para todo mundo — todos
  os testes de câmera existentes quebrariam.
- `get_root() is self` **também não**: `Scene` é um `Node`, e cena dentro de
  cena é o caminho previsto. Ali a raiz seria a cena de fora, e a de dentro
  perderia o próprio enquadramento.

O que responde certo nos dois arranjos é ascendência — `is_ancestor_of`, que o
`Node` já tinha.

### Arquitetura

**~~`Vector2D` mutável é a decisão que mais custa.~~ Congelado.** Três
comentários no código eram contornos da mesma decisão (`transform.py`, `rect.py`
— "a pior das duas garantias" — e `conftest.py`), e a defesa não cobria tudo:
`a.transform.position = b.transform.position` ligava dois nós em silêncio.

O efeito dominó foi todo de subtração, como previsto:

- `Vector2D.copy()` deixou de existir — não há o que copiar de um valor;
- `Transform` trocou os dois `default_factory` por defaults literais, porque
  compartilhar a mesma instância de `(0, 0)` entre todos os nós virou inofensivo
  (verificado: `a.position is b.position` é `True`, e ninguém consegue escrever
  nela);
- `Transform.copy()` virou uma linha, e continua existindo só porque o
  `Transform` em si segue mutável — de propósito, para que
  `no.transform.rotation += x` continue sendo a ergonomia do código de jogo;
- o vetor virou hashável, então serve de chave e de membro de conjunto;
- seis testes que defendiam contra aliasing viraram testes de imutabilidade —
  a garantia deixou de depender de alguém lembrar de copiar.

No `main.py` o que quebrou foi só a escrita em componente. O estilo que substituiu
(`horizontal`/`vertical` acumulados em escalares, vetor montado uma vez) ficou
mais direto do que o original.

**~~A transform mundial é recalculada a cada chamada.~~ Resolvida.**
Medido com o `SpyRenderer` da própria suíte, sem abrir janela:

| cenário | antes do passo 6 | passo 6 (congelar) | passo 7 (bounds) |
|---|---|---|---|
| desenhar 6 nós encadeados | 63 subidas de cadeia | 63 | **21** (o ideal é 6) |
| 500 nós rasos | 3,68 ms/frame | 5,24 ms/frame | **2,82 ms/frame** |
| 2000 nós a profundidade 4 | 28,16 ms/frame | 41,54 ms/frame | **17,70 ms/frame** |
| orçamento a 60 fps | 16,6 ms | 16,6 ms | 16,6 ms |

**Congelar o `Vector2D` custou cerca de 42% do tempo de render**, e isso precisa
ficar escrito. Um `dataclass` frozen constrói via `object.__setattr__` — medido,
308 ns por vetor contra 113 ns de um dataclass mutável de mesma forma, 2,7x — e o
caminho de desenho antigo construía muitos: três subidas de cadeia por nó, cada
uma alocando um `Transform` e vários vetores por nível.

O passo 6 foi, isolado, uma **piora de performance** trocada por correção e por
possibilidade. O passo 7 devolveu a dívida inteira e sobrou: o número de hoje é
melhor que o de *antes* de congelar, em ambos os cenários. Não porque a
construção de vetor tenha ficado barata — ficou tudo igual —, mas porque o
caminho de desenho parou de fazer o mesmo trabalho três vezes.

Duas coisas que a medição mostrou e que não eram óbvias:

- **O código de jogo não migrado também ficou mais rápido.** O idioma antigo
  caiu de 63 para 42 subidas sozinho, porque `get_world_top_left()` custava duas
  resoluções — uma pelo centro, outra pelo tamanho — e agora custa uma. Quem
  nunca ouvir falar de `get_world_bounds()` já leva um terço do ganho.
- **Ainda estourava o orçamento no cenário profundo**, por pouco. 17,70 ms
  contra 16,6 ms. O que sobrava era o custo que cresce com a *profundidade* — as
  21 subidas de cadeia contra as 6 ideais. É o que o passo 8 atacou.

#### O passo 8: o cache

Aqui a tabela de uma coluna só não serve mais, porque um cache não tem *um*
número: tem um por regime de escrita. As duas colunas foram medidas no mesmo
processo, o braço "sem cache" reconstruindo o código do passo 7 — inclusive o
`Transform` como `dataclass` simples, para que o custo de *escrita* apareça dos
dois lados.

Os absolutos da coluna "sem cache" não batem com a tabela acima (3,32 contra
2,82) porque o arnês é outro: este reconstrói a árvore a cada repetição e o nó
legado carrega uma indireção a mais. **Só a razão entre as duas colunas quer
dizer alguma coisa aqui**; comparar de uma tabela para a outra, não.

| regime | cenário | sem cache | com cache |
|---|---|---|---|
| **parado** — nada escreve | 6 encadeados | 21 subidas | **6** |
| | 500 rasos | 3,32 ms | **1,96 ms** (−41%) |
| | 2000 a prof. 4 | 20,91 ms | **8,53 ms** (−59%) |
| **raiz move** — um nó no topo por frame | 500 rasos | 3,30 ms | **1,94 ms** (−41%) |
| | 2000 a prof. 4 | 21,55 ms | **8,41 ms** (−61%) |
| **tudo move** — todo nó escreve por frame | 500 rasos | 3,48 ms | 3,71 ms (**+7%**) |
| | 2000 a prof. 4 | 21,55 ms | **15,07 ms** (−30%) |
| **escrita ociosa** — todo nó reescreve o mesmo valor | 500 rasos | 3,30 ms | **2,04 ms** (−38%) |
| | 2000 a prof. 4 | 21,78 ms | **8,74 ms** (−60%) |

**O cenário profundo passou a caber no orçamento de 16,6 ms em todos os
regimes**, que era o objetivo. E as 6 subidas para 6 nós encadeados, que o
passo 7 deixou em 21, chegaram.

Três leituras que a medição deu e que não estavam no plano:

- **O ganho não depende de as coisas ficarem paradas.** O intuitivo é que um
  cache só ajuda quando nada muda; aqui, com *tudo* se movendo, o cenário
  profundo ainda cai 30%. O motivo é a ordem da travessia: pai desenha antes de
  filho, então mesmo recém-invalidado o pai já está recalculado quando o filho
  pergunta. O cache transforma o render de O(N × profundidade) em **O(N)
  independentemente do quanto se moveu**.
- **Um regime piora: árvore rasa com tudo se movendo, +7%.** É honesto que
  piore. A profundidade é 1, não há cadeia para economizar, e o que sobra é o
  custo de interceptar a escrita. Vale trocar 7% no pior caso por 41-61% em
  todos os outros — mas o número fica escrito, não escondido.
- **A escrita ociosa custa o mesmo que ficar parado.** É a guarda de igualdade
  do `Transform` fazendo efeito: sem ela, esse regime — o `rotation = 0.0`
  incondicional do `main.py` — teria sido o pior de todos.

`TestCacheCost` conta resoluções por nó e tranca o ganho; `TestChainClimbs` faz
o mesmo para o passo 7. Sem eles a peça continuaria correta e voltaria a ser
cara na primeira vez que alguém a reescrevesse, e nenhum teste de valor
perceberia.

E um teste que vale destacar: `TestCacheAgreesWithAFreshComputation` roda uma
sequência roteirizada de mexidas — mover, girar, escalar, reparentar, remover,
trocar a transform inteira, reescrever o mesmo valor — e depois de **cada uma**
compara os quatro nós com a implementação sem cache do passo 7, mantida no
arquivo de teste como oráculo. Um cache errado não levanta exceção: devolve o
valor de ontem, e o jogo desenha no lugar errado em silêncio. A única defesa é
perguntar a alguém que não tem cache.

**~~A ordem de desenho é a ordem da árvore.~~ Feito.** O `Hud` chamava
`reset_camera()` dentro do `on_render` e dependia de ser o último filho. A cena
passou a ter duas subárvores — `world` e `ui` —, e é ela que decide o espaço de
cada passada; o `Hud` perdeu a linha de `reset_camera` e não ganhou nenhuma no
lugar. As decisões estão em *Conceitos*, com 17 testes atrás delas.

Duas coisas que a implementação mostrou e que não estavam no plano:

- **A camada dá o menu de pausa de graça.** `scene.world.active = False` congela
  o mundo e mantém a UI viva — os dois portões do `Node` aplicados a uma camada
  inteira. Era a justificativa que faltava para `world` existir, já que filho
  direto da cena sempre desenhou em espaço de mundo.
- **Dois testes antigos afirmavam que uma `Scene` nasce vazia.** Não nasce mais:
  as camadas são filhas comuns, criadas no construtor. Os dois passaram a cobrar
  o que de fato queriam dizer — que o nó marcado saiu da árvore, e não que a
  lista de filhos ficou vazia.

`z_index` dentro de uma camada continua fora, até um jogo pedir.

**~~O código de jogo enumera teclas onde deveria nomear intenções.~~ Feito.**
`ActionMap` mora no núcleo e só fala com a porta `Input`, então é exercitável sem
backend nenhum — os 37 testes novos rodam sem abrir janela. No `main.py` o
`on_update` do `Player` caiu de oito linhas de teclado para uma chamada de
`get_vector`, e a normalização manual de diagonal sumiu junto: ela agora é
garantia do método, e não lembrança de quem escreve o nó.

O que a implementação acrescentou ao plano foram as arestas de ação com **mais de
uma tecla** — `is_just_pressed`/`is_just_released` perguntam se a *ação* mudou de
estado, não se alguma tecla mudou. Estão em *Conceitos*, com teste cada uma.

**~~`Rect` só serve de região de sprite.~~ Completo.** Ganhou `center`,
`from_center_size`, `contains`, `intersects` e `normalized`, e virou o tipo de
retorno de `get_world_bounds()` — a mesma peça servindo de ergonomia de desenho
e de base de colisão. As decisões de fronteira (semiaberto, área zero,
espelhamento) estão em *Conceitos*, com 25 testes atrás delas.

O que ainda **não** existe é resposta a colisão: `intersects` diz *se* houve, e
nada sobre profundidade de penetração ou eixo de separação. Empurrar o jogador
para fora da parede é decisão de jogo, e ela entra quando um jogo pedir.

**Arestas menores.** O tamanho da tela vive em dois lugares
(`ApplicationConfig` e os argumentos da `Camera` no `main.py`) — mudar a
resolução em um desenquadra o outro em silêncio. E não há `find_child(name)`:
achar um nó só funciona guardando a referência na construção da cena.

### Processo

**~~O projeto não está sob controle de versão.~~ Resolvido.** `git init` feito, e
o `.gitignore` veio junto — não era opcional, porque o `venv/` mora dentro da
árvore e o primeiro `git add .` teria levado o Pyxel, o mypy e o resto junto.
Além dele, ficam de fora o bytecode, o `*.egg-info/` da instalação editável e os
três caches de ferramenta (`.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`) —
estes últimos já escrevem um `.gitignore` próprio lá dentro, e estão listados
para que a regra não dependa de a ferramenta continuar fazendo isso.

**~~O rigor prometido no `pyproject.toml` nunca foi exercido.~~ Resolvido.**
`ruff`, `black` e `mypy --strict` estavam declarados e nenhum instalado. A linha
de base, quando finalmente rodaram, foi pequena: 8 achados de ruff, 13 arquivos
fora do formato do black, e 4 erros de mypy — **todos em `tests/`, nenhum em
`engine/`**, que passou limpo no `--strict` de primeira. Hoje as três passam sem
nada.

Dois detalhes que a primeira execução revelou e que valia registrar:

- **O mypy não conseguia nem começar.** `tests/` não tinha nenhum `__init__.py`,
  então `conftest.py` resolvia ao mesmo tempo como `conftest` e como
  `tests.conftest` e ele abortava antes de checar qualquer coisa. A correção que
  o próprio mypy sugere — adicionar os `__init__.py` — é a mesma que o
  `namespaces = false` do pyproject já defendia para `engine*`. A regra agora
  vale para o projeto inteiro.
- **O `[tool.black]` não tinha `target-version`.** Sem ele o black infere a
  versão mais nova que conhece e passa a formatar para uma sintaxe que o
  interpretador local não sabe ler — a checagem de equivalência dele falha antes
  de comparar coisa alguma. Fixado em `py311`, alinhado com o `requires-python` e
  com o ruff.

**Acabamento.** `pyxel_time_provider.py` está comentado em inglês enquanto todo o
resto está em português. E o `main.py` faz papel de exemplo na raiz enquanto
`games/` está vazia — mover para `games/demo/` deixaria a raiz só com o que é
distribuível.

### Arredondar para a grade: a decisão

**Resolvido — a engine não arredonda.** O adaptador recebe float e repassa float,
em `draw_rect`, `draw_text`, `draw_sprite` e `set_camera`. Três testes fixam
isso, para que ninguém reintroduza `int()` em um método só.

O motivo de ser uma decisão e não um detalhe: `size` ainda vinha truncado
enquanto a posição já passava em float, e o comentário do `draw_rect` afirmava o
contrário do que o código fazia. **Prender o desenho à grade é política, e
política precisa valer inteira ou não valer** — arredondar num lugar só daria um
retângulo alinhado e um sprite subpixel na mesma cena, com a câmera fracionária
por baixo dos dois.

Se um dia a pixel art pedir *snapping*, ele entra como uma função única aplicada
a posição, tamanho e câmera junto — e com `round()`, não `int()`, que trunca em
direção ao zero e desloca meio pixel em coordenada negativa. A câmera é onde mais
apareceria: seguindo o jogador a 70 px/s o offset é fracionário quase sempre, e
cenário inteiro tremendo é o sintoma clássico.

### Ordem sugerida

Não é lista de desejos, é sequência: cada passo torna o seguinte mais seguro ou
mais barato.

1. ~~**`git init` + `.gitignore`**~~ — **feito.** Antes de qualquer coisa, porque
   tudo que vem depois é refactor, e refactor sem histórico é aposta.
2. ~~**Instalar as dev deps e rodar ruff, black e mypy**~~ — **feito.** As três
   passam limpas, e daqui em diante o que aparecer é regressão, não dívida.
3. ~~**Fila de remoção na raiz**~~ — **feito.** 10 testes novos cobrindo o bug e
   as três arestas do novo desenho.
4. ~~**Câmera órfã e o comentário obsoleto do `draw_rect`**~~ — **feito.**
   A guarda de câmera pergunta por ascendência; o arredondamento virou decisão
   explícita (a engine não arredonda) com testes que a travam.
5. ~~**Reorganizar as pastas**~~ — **feito.** 38 arquivos movidos, imports
   reescritos por script, zero mudança de comportamento. Saiu junto a superfície
   pública em `engine/__init__.py`.
6. ~~**`Vector2D` imutável**~~ — **feito.** O refactor de fundação. Cobrou 42%
   de performance de render, que os passos 7 e 8 devolvem com juros.
7. ~~**`Rect` completo + `get_world_bounds()`**~~ — **feito.** A mesma peça vista
   de dois lados: ergonomia de desenho e base de colisão. Render 46% mais rápido
   no cenário raso e 59% no profundo — a dívida do passo 6 paga com juros, como
   previsto. 39 testes novos.
8. ~~**Cache de transform com bandeira suja**~~ — **feito.** O cenário profundo
   passou a caber no orçamento de 16,6 ms em todos os regimes de escrita, e as
   6 subidas para 6 nós chegaram. Custou o `Transform` virar properties escritas
   à mão — a medição mostrou que um `__setattr__` encarece a *construção* em 20x,
   e o caminho de render constrói muito. 41 testes novos, um deles conferindo
   cada mexida contra a implementação sem cache.
9. ~~**Mapa de ações**~~ — **feito.** O primeiro ganho que se sente escrevendo
   jogo, e não engine: o `on_update` do `Player` passou a nomear intenções, e a
   lista de teclas passou a existir em um lugar só. 37 testes novos, a maior
   parte deles nas arestas de ação com mais de uma tecla.
10. ~~**Camadas de render**~~ — **feito.** `world` e `ui` como subárvores da
    cena, e a cena decidindo o espaço de cada passada. O `Hud` deixou de mexer no
    estado do renderer e a ordem de desenho deixou de depender da posição na
    lista de filhos. 17 testes novos.
