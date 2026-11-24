# Arquitetura e fluxos dos algoritmos

Esta página apresenta a estrutura efetivamente implementada em `src/`. Os
diagramas de chamadas e UML são regenerados por análise estática; os fluxos
conceituais foram deliberadamente resumidos para evidenciar decisões do
algoritmo sem reproduzir cada detalhe de instrumentação.

## Visão geral

`tsplib` concentra a leitura e a matriz de custos, reutilizada por todas as
estratégias. `initial_solutions` registra as cinco formas de criar a incumbente
do Branch-and-Bound. As duas aproximações e suas subrotinas compartilhadas
ficam em `approximation`. A execução em lote separa o orquestrador
`experiment_runner` do processo isolado `experiment_worker`, que chama o mesmo
solver usado pela CLI.

### Fluxo geral dos experimentos

Este esquema mostra somente o caminho principal: descobrir as instâncias,
executar cada configuração isoladamente, salvar os artefatos e analisar o CSV
consolidado. Detalhes internos do solver ficam nos fluxos posteriores.

<!-- BEGIN GENERATED: workflow-experiments -->
```mermaid
%% Fluxo conceitual curado; gerado por scripts/generate_diagrams.py.
flowchart TD
  instances["Instâncias<br/>.tsp"] --> runner["Executor do lote"]
  runner --> worker["Worker isolado<br/>warm-start + Branch-and-Bound"]
  worker --> save["Salvar resultado"]
  save --> artifacts["Rota, checkpoint,<br/>JSON e log"]
  save --> csv[("results.csv")]
  csv --> analysis["Features, gaps<br/>e modelos"]
  analysis --> enriched[("CSV enriquecido<br/>+ resumo")]
```
<!-- END GENERATED: workflow-experiments -->

### Dependências entre módulos (Pyreverse)

As setas indicam importações entre módulos do pacote.

<!-- BEGIN GENERATED: uml-modules -->
```mermaid
%% Gerado pelo Pyreverse; não edite manualmente.
classDiagram
  class traveling_salesman_optimization {
  }
  class approximation {
  }
  class branch_and_bound {
  }
  class empirical_analysis {
  }
  class experiment_io {
  }
  class experiment_runner {
  }
  class experiment_worker {
  }
  class initial_solutions {
  }
  class main {
  }
  class phase_profiling {
  }
  class process_metrics {
  }
  class tsplib {
  }
  traveling_salesman_optimization --> approximation
  traveling_salesman_optimization --> branch_and_bound
  traveling_salesman_optimization --> initial_solutions
  traveling_salesman_optimization --> tsplib
  approximation --> phase_profiling
  approximation --> tsplib
  branch_and_bound --> initial_solutions
  branch_and_bound --> phase_profiling
  branch_and_bound --> tsplib
  empirical_analysis --> approximation
  empirical_analysis --> experiment_io
  empirical_analysis --> initial_solutions
  empirical_analysis --> tsplib
  experiment_runner --> experiment_io
  experiment_runner --> initial_solutions
  experiment_worker --> branch_and_bound
  experiment_worker --> experiment_io
  experiment_worker --> initial_solutions
  experiment_worker --> process_metrics
  experiment_worker --> tsplib
  initial_solutions --> approximation
  initial_solutions --> tsplib
  main --> branch_and_bound
  main --> initial_solutions
  main --> tsplib
```
<!-- END GENERATED: uml-modules -->

### Classes e contratos do domínio (Pyreverse)

O recorte se concentra nos três módulos do domínio para manter em foco a
instância TSP, o resultado instrumentado e o contrato substituível das
estratégias iniciais.

<!-- BEGIN GENERATED: uml-classes -->
```mermaid
%% Gerado pelo Pyreverse; não edite manualmente.
classDiagram
  class BranchAndBoundResult {
    checkpoint_calls : int
    checkpoint_seconds : float
    cost : int
    eulerian_circuit_calls : int
    eulerian_circuit_process_peak_bytes : int
    eulerian_circuit_seconds : float
    expanded_nodes : int
    generated_nodes : int
    initial_cost : int
    initialization_seconds : float
    lower_bound_calls : int
    lower_bound_seconds : float
    matching_calls : int
    matching_process_peak_bytes : int
    matching_seconds : float
    max_depth : int
    mst_calls : int
    mst_process_peak_bytes : int
    mst_seconds : float
    optimal_cost : int | None
    pruned_nodes : int
    route : tuple[int, ...]
    search_seconds : float
    shortcut_calls : int
    shortcut_process_peak_bytes : int
    shortcut_seconds : float
    solver_total_seconds : float
    status : Literal
  }
  class InitialRouteStrategy {
  }
  class TSPInstance {
    coordinates : tuple[tuple[float, float], ...]
    dimension : int
    distances : tuple
    name : str
    vertex_ids : tuple[int, ...]
    route_cost(route: Sequence[int]) int
  }
  class _DeadlineExceeded {
  }
  class _RouteNode {
    depth : int
    parent : _RouteNode | None
    vertex : int
  }
```
<!-- END GENERATED: uml-classes -->

## Chamadas e reutilização de código

Os grafos abaixo são produzidos pelo Code2flow. Funções de entrada aparecem
em azul. Chamadas repetidas entre o mesmo par são condensadas em uma única
seta e os números de linha são omitidos para reduzir ruído nos diffs.

### Caminho da CLI ao solver

<!-- BEGIN GENERATED: calls-cli -->
```mermaid
%% Gerado por scripts/generate_diagrams.py a partir da saída do Code2flow.
flowchart LR
  subgraph module_branch_and_bound["branch_and_bound.py"]
    direction TB
    n0["_cheapest_allowed_edges_sum()"]
    n1["_incident_vertices_by_cost()"]
    n2["_materialize_route()"]
    n3["_two_edges_lower_bound()"]
    n4["solve_branch_and_bound()"]
  end
  subgraph module_main["main.py"]
    direction TB
    n5["main()"]
  end
  subgraph module_phase_profiling["phase_profiling.py"]
    direction TB
    n6["ApproximationProfile.value()"]
    n7["collect_approximation_profile()"]
  end
  subgraph module_tsplib["tsplib.py"]
    direction TB
    n8["TSPInstance.route_cost()"]
    n9["_build_distance_matrix()"]
    n10["_parse_header()"]
    n11["calculate_route_cost()"]
    n12["read_tsplib()"]
  end
  n3 --> n0
  n4 --> n1
  n4 --> n2
  n4 --> n3
  n4 --> n6
  n4 --> n7
  n4 --> n8
  n5 --> n4
  n5 --> n12
  n8 --> n11
  n12 --> n9
  n12 --> n10
  classDef entry fill:#dbeafe,stroke:#2563eb,stroke-width:2px
  class n5 entry
```
<!-- END GENERATED: calls-cli -->

### Núcleo do Branch-and-Bound

<!-- BEGIN GENERATED: calls-branch-and-bound -->
```mermaid
%% Gerado por scripts/generate_diagrams.py a partir da saída do Code2flow.
flowchart LR
  subgraph module_branch_and_bound["branch_and_bound.py"]
    direction TB
    n0["_cheapest_allowed_edges_sum()"]
    n1["_incident_vertices_by_cost()"]
    n2["_materialize_route()"]
    n3["_two_edges_lower_bound()"]
    n4["solve_branch_and_bound()"]
  end
  subgraph module_phase_profiling["phase_profiling.py"]
    direction TB
    n5["ApproximationProfile.value()"]
    n6["collect_approximation_profile()"]
  end
  subgraph module_tsplib["tsplib.py"]
    direction TB
    n7["TSPInstance.route_cost()"]
    n8["calculate_route_cost()"]
  end
  n3 --> n0
  n4 --> n1
  n4 --> n2
  n4 --> n3
  n4 --> n5
  n4 --> n6
  n4 --> n7
  n7 --> n8
  classDef entry fill:#dbeafe,stroke:#2563eb,stroke-width:2px
  class n4 entry
```
<!-- END GENERATED: calls-branch-and-bound -->

### Chamadas da estratégia trivial

A rota trivial é autocontida; por isso, seu grafo possui apenas a função de
entrada.

<!-- BEGIN GENERATED: calls-strategy-trivial -->
```mermaid
%% Gerado por scripts/generate_diagrams.py a partir da saída do Code2flow.
flowchart LR
  subgraph module_initial_solutions["initial_solutions.py"]
    direction TB
    n0["trivial_initial_route()"]
  end
  classDef entry fill:#dbeafe,stroke:#2563eb,stroke-width:2px
  class n0 entry
```
<!-- END GENERATED: calls-strategy-trivial -->

### Chamadas do Vizinho Mais Próximo

O Vizinho Mais Próximo também é autocontido. Operações de coleção e acesso à
matriz não aparecem como funções independentes no Code2flow.

<!-- BEGIN GENERATED: calls-strategy-nearest-neighbor -->
```mermaid
%% Gerado por scripts/generate_diagrams.py a partir da saída do Code2flow.
flowchart LR
  subgraph module_initial_solutions["initial_solutions.py"]
    direction TB
    n0["nearest_neighbor_initial_route()"]
  end
  classDef entry fill:#dbeafe,stroke:#2563eb,stroke-width:2px
  class n0 entry
```
<!-- END GENERATED: calls-strategy-nearest-neighbor -->

### Chamadas da inserção pelo fecho convexo

<!-- BEGIN GENERATED: calls-strategy-convex-hull -->
```mermaid
%% Gerado por scripts/generate_diagrams.py a partir da saída do Code2flow.
flowchart LR
  subgraph module_initial_solutions["initial_solutions.py"]
    direction TB
    n0["_convex_hull_vertices()"]
    n1["_cross_product()"]
    n2["convex_hull_insertion_initial_route()"]
  end
  n0 --> n1
  n2 --> n0
  classDef entry fill:#dbeafe,stroke:#2563eb,stroke-width:2px
  class n2 entry
```
<!-- END GENERATED: calls-strategy-convex-hull -->

### Chamadas de Twice-around-the-tree

<!-- BEGIN GENERATED: calls-strategy-twice-around-tree -->
```mermaid
%% Gerado por scripts/generate_diagrams.py a partir da saída do Code2flow.
flowchart LR
  subgraph module_approximation["approximation.py"]
    direction TB
    n0["_eulerian_circuit()"]
    n1["_eulerian_to_hamiltonian()"]
    n2["_minimum_spanning_tree_edges()"]
    n3["twice_around_tree_route()"]
  end
  n3 --> n0
  n3 --> n1
  n3 --> n2
  classDef entry fill:#dbeafe,stroke:#2563eb,stroke-width:2px
  class n3 entry
```
<!-- END GENERATED: calls-strategy-twice-around-tree -->

### Chamadas de Christofides

<!-- BEGIN GENERATED: calls-strategy-christofides -->
```mermaid
%% Gerado por scripts/generate_diagrams.py a partir da saída do Code2flow.
flowchart LR
  subgraph module_approximation["approximation.py"]
    direction TB
    n0["_eulerian_circuit()"]
    n1["_eulerian_to_hamiltonian()"]
    n2["_minimum_spanning_tree_edges()"]
    n3["_minimum_weight_perfect_matching()"]
    n4["christofides_route()"]
  end
  n4 --> n0
  n4 --> n1
  n4 --> n2
  n4 --> n3
  classDef entry fill:#dbeafe,stroke:#2563eb,stroke-width:2px
  class n4 entry
```
<!-- END GENERATED: calls-strategy-christofides -->

## Fluxos principais

Estes fluxos são uma visão curada da implementação. Eles complementam os
grafos automáticos mostrando laços e decisões que um grafo de chamadas não
representa bem.

### Branch-and-Bound exato

```mermaid
flowchart TD
  start([Instância TSP]) --> validate[Validar entrada e prazo]
  validate --> warm[Executar estratégia inicial]
  warm --> incumbent[Normalizar rota e calcular incumbente]
  incumbent --> root[Calcular limite inferior da raiz]
  root --> queue[(Fila de prioridade pelo menor limite)]
  queue --> empty{Fronteira vazia?}
  empty -- Sim --> optimal([Ótimo comprovado])
  empty -- Não --> deadline{Prazo expirou?}
  deadline -- Sim --> timeout([Retornar incumbente com timeout])
  deadline -- Não --> pop[Remover estado de menor limite]
  pop --> stale{Estado foi dominado?}
  stale -- Sim --> count_pruned[Contabilizar estado podado]
  stale -- Não --> prune{Limite >= incumbente?}
  prune -- Sim --> count_frontier[Contabilizar estado e fronteira restante]
  count_frontier --> optimal
  count_pruned --> queue
  prune -- Não --> complete{Rota completa?}
  complete -- Sim --> improve[Atualizar incumbente]
  improve --> queue
  complete -- Não --> expand[Gerar filhos não visitados]
  expand --> dominance{Custo melhora o estado equivalente?}
  dominance -- Não --> count_child[Contabilizar filho podado]
  dominance -- Sim --> bounds[Calcular limite inferior]
  bounds --> child_prune{Limite >= incumbente?}
  child_prune -- Sim --> count_child
  count_child --> queue
  child_prune -- Não --> queue
```

O limite inferior soma as duas arestas incidentes mais baratas ainda
permitidas em cada vértice, respeitando a rota parcial, e divide a soma por
dois. A fila implementa exploração *best-first*. Estados equivalentes mantêm
somente o menor custo parcial, e seus prefixos compartilham nós ligados ao pai;
a rota completa é materializada apenas quando se torna incumbente. Checkpoints
são disparados em pontos cooperativos do laço sem alterar a ordem da busca.
Como a heap remove primeiro o menor limite, quando esse valor já alcança a
incumbente toda a fronteira restante pode ser contabilizada como podada e a
prova termina imediatamente.

### Estratégias de incumbente inicial

```mermaid
flowchart LR
  subgraph trivial[Trivial]
    t1[Ordem do arquivo] --> t2[Rota 0..n-1]
  end
  subgraph nearest[Vizinho mais próximo]
    n1[Começar em 0] --> n2[Escolher não visitado mais próximo]
    n2 --> n3{Restam vértices?}
    n3 -- Sim --> n2
    n3 -- Não --> n4[Rota completa]
  end
  subgraph hull[Inserção pelo fecho convexo]
    h1[Cadeia monotônica] --> h2[Ciclo do fecho]
    h2 --> h3[Inserir par vértice/aresta de menor acréscimo]
    h3 --> h4{Restam vértices?}
    h4 -- Sim --> h3
    h4 -- Não --> h5[Rotacionar para origem 0]
  end
  subgraph twice[Twice-around-the-tree]
    a1[AGM por Prim] --> a2[Duplicar arestas]
    a2 --> a3[Circuito euleriano por Hierholzer]
    a3 --> a4[Remover visitas repetidas]
  end
  subgraph christofides[Christofides]
    c1[AGM por Prim] --> c2[Vértices de grau ímpar]
    c2 --> c3[Matching perfeito mínimo]
    c3 --> c4[Unir AGM e matching]
    c4 --> c5[Circuito euleriano]
    c5 --> c6[Remover visitas repetidas]
  end
```

As cinco rotas usam índices internos, começam no índice zero e não repetem a
origem no fim. O solver valida a permutação e calcula o custo pela mesma matriz
`EUC_2D`, evitando divergência entre estratégias.

## Como regenerar

Instale as dependências específicas de documentação no ambiente virtual:

```bash
python -m pip install -e ".[docs]"
```

Para renderizar as figuras PDF usadas em `docs/report/main.tex`, o executável
`dot` do [Graphviz](https://graphviz.org/download/) também deve estar disponível
no `PATH`. Se ele estiver em outro local, informe-o com `--dot CAMINHO`.

Depois de alterar o código em `src/`, execute:

```bash
python scripts/generate_diagrams.py
```

O comando recria os arquivos Mermaid em `docs/diagrams/generated/` e sincroniza
os blocos delimitados por `BEGIN GENERATED` nesta página. As fontes DOT ficam
na mesma pasta e os PDFs do artigo são escritos em `docs/report/figures/`. Não
edite esses blocos ou arquivos gerados manualmente; os fluxos conceituais fora
dos marcadores podem ser ajustados quando uma mudança alterar as etapas do
algoritmo.

Code2flow e Pyreverse fazem análise estática: chamadas dinâmicas por meio do
registro `INITIAL_ROUTE_STRATEGIES` não são inferidas como arestas. Por isso,
cada estratégia possui uma lista explícita de funções no gerador, inclusive as
duas entradas autocontidas. O fluxo geral dos experimentos é conceitual e não é
atribuído ao Code2flow.
