# Executor de experimentos

O lote já coletado para a inicialização trivial, com configuração, tabela de
resultados, interpretação preliminar e limitações, está documentado em
[`docs/analysis/trivial-baseline.md`](../docs/analysis/trivial-baseline.md).
A adaptação e a preparação do teste do limite das duas arestas estão em
[`docs/analysis/lower-bound-two-edges.md`](../docs/analysis/lower-bound-two-edges.md).

O módulo `traveling_salesman_optimization.experiment_runner` executa o
Branch-and-Bound sequencialmente, com um processo novo para cada par
instância–repetição. As cinco estratégias registradas são `trivial`,
`nearest_neighbor`, `convex_hull`, `twice_around_tree` e `christofides`; todas
usam a mesma interface do solver e do executor.

## Comandos

No Windows PowerShell, um lote completo com os padrões de uma repetição e
1.800 segundos por execução pode ser iniciado com:

```powershell
.\scripts\run_experiments.bat data\instances `
  --output-dir experiments\results\trivial
```

Uma lista explícita, três repetições e checkpoints a cada 30 segundos:

```powershell
.\scripts\run_experiments.bat `
  data\instances\ulysses16.tsp data\instances\gr24.tsp `
  --output-dir experiments\results\trivial `
  --strategy trivial --repetitions 3 `
  --timeout-seconds 1800 --checkpoint-interval-seconds 30
```

No Linux ou macOS, substitua o script por:

```bash
python scripts/tasks.py experiment data/instances \
  --output-dir experiments/results/trivial
```

O mesmo comando retoma o lote: execuções `optimal` e `timeout` com o mesmo
identificador são puladas, enquanto erros são tentados novamente. Para repetir
explicitamente as execuções selecionadas e substituir suas linhas, acrescente
`--rerun`. O CSV nunca mantém duas linhas com o mesmo `run_id`.

Pastas de entrada são percorridas recursivamente. O identificador combina a
configuração, o caminho absoluto, o SHA-256 do conteúdo da instância e a
repetição; uma alteração na instância ou em um parâmetro relevante cria outra
execução reproduzível.

Para comparar os warm-starts com o mesmo painel, repetições, prazo e versão do
código, prefira uma única invocação com `--all-strategies`. A opção
`--strategy` também pode ser repetida para selecionar um subconjunto. Cada
estratégia recebe seu próprio `config_id`, mas todas são persistidas no mesmo
CSV e na mesma invocação. `initialization_seconds` inclui a heurística completa.

O solver usa exclusivamente o limite das duas arestas incidentes apresentado
na Aula 12. A configuração canônica registra `lower_bound: "two_edges"`; não há
opção de linha de comando para selecionar outro limite. O schema 3 removeu as
colunas legadas da AGM. O schema 4 acrescenta impressão digital dos fontes,
runtime e dependências, nós gerados e profiling das aproximações. Dentro desse
schema, `instrumentation_version=5` identifica a semântica atual: dominância de
estados, poda antes da heap e contagem de todo filho considerado como gerado.
Resultados dos schemas 1 a 3 continuam intactos, mas uma nova execução deve
usar outra pasta de saída (ou um CSV previamente migrado).

## Arquivos produzidos

Para uma pasta passada em `--output-dir`, são criados:

- `results.csv`: tabela consolidada, regravada atomicamente após cada execução;
- `configurations/config-<config_id>.json`: parâmetros canônicos, versões,
  plataforma, Python, CPU e estado do Git;
- `invocations/*.json`: entradas, hashes, número de repetições, comando e uso
  de `--rerun` em cada chamada do lote;
- `specs/<run_id>.json`: especificação fornecida ao processo isolado;
- `checkpoints/<run_id>.json`: último retrato parcial válido;
- `runs/<run_id>.json`: registro final detalhado;
- `routes/<run_id>.tour`: melhor ciclo viável em formato TSPLIB TOUR;
- `logs/<run_id>.log`: saída e traceback do processo worker.

JSON, TOUR e CSV usam um temporário no mesmo diretório, `fsync` e
`os.replace`, de modo que um arquivo parcialmente escrito nunca toma o lugar
da última versão válida. Falhas individuais recebem `status=error`, são
persistidas e não interrompem as execuções seguintes. `Ctrl+C` encerra o
worker atual, consolida seu último checkpoint como erro recuperável e para o
lote; uma retomada tenta essa execução novamente.

## Semântica das métricas

Todas as durações internas usam `time.perf_counter`, que é monotônico:

- `instance_load_seconds` mede leitura, validação e construção da matriz de
  distâncias; fica fora do solver;
- `initialization_seconds` mede a chamada da estratégia, validação/rotação da
  rota inicial e cálculo de seu custo;
- `search_seconds` começa depois da incumbente inicial e inclui limite da raiz,
  fila de prioridade, expansão/poda, verificações de prazo e checkpoints;
- `solver_total_seconds = initialization_seconds + search_seconds`;
- `lower_bound_seconds` está contido em `search_seconds`;
- `checkpoint_seconds` está contido em `search_seconds`;
- `executor_wall_seconds` inclui inicialização do interpretador, leitura da
  instância, solver, serialização e encerramento do processo. Ele não é um
  componente de `solver_total_seconds`.

Portanto, tempos de limite inferior e checkpoint não devem ser somados ao
tempo de busca. `lower_bound_calls` conta chamadas iniciadas, e
`lower_bound_seconds` contém todo o custo do LB das duas arestas.

`expanded_nodes` conta estados removidos da fila que geram filhos.
`pruned_nodes` inclui estados descartados por limite inferior, por dominância
de outro prefixo que alcança o mesmo `(vértice atual, conjunto restante)` com
custo menor ou igual e, ao concluir a prova, os estados remanescentes cuja chave na heap
já é maior ou igual à incumbente. Folhas viáveis não são expansões.
`max_depth` é o maior número de arestas escolhidas depois da origem (raiz zero,
ciclo completo `n - 1`).

`generated_nodes` conta a raiz e cada filho considerado. Um filho dominado é
descartado antes do cálculo do limite, enquanto um filho cujo limite não pode
melhorar a incumbente é descartado antes da inserção na heap. Por isso,
`lower_bound_calls` pode ser menor que `generated_nodes`, e o total gerado não
é necessariamente a soma de expandidos e podados.

`mst_*`, `matching_*`, `eulerian_circuit_*` e `shortcut_*` medem chamadas e
tempo das fases executadas durante o warm-start. Os campos
`*_process_peak_bytes` são o high-water mark do processo observado ao final da
fase, não memória exclusiva ou incremental, e não são aditivos.

`initial_route_cost` é o limite superior inicial; `best_route_cost` é sempre o
custo da melhor rota preservada. `optimal_cost` só recebe esse custo em
`status=optimal`; em `timeout` e `error`, recebe o literal `NA`, como exige o
enunciado. O worker recalcula o custo da rota antes de aceitar um resultado
final.

## Prazo, checkpoint e memória

O prazo por execução começa antes da leitura da instância; o worker desconta
esse tempo antes de entregar o restante ao solver. O solver o verifica
cooperativamente no laço da busca e na geração de filhos. Ao expirar,
devolve `timeout` com a incumbente, contadores e tempos parciais. O executor
espera ainda `--external-grace-seconds` (10 por padrão) e então usa
`terminate`/`kill` sobre o grupo do worker como salvaguarda, convertendo o
último checkpoint válido em resultado de timeout. A rota é armazenada no JSON
do checkpoint e o `.tour` é rematerializado desse mesmo retrato.

## Análise de sensibilidade e qualidade

O módulo `traveling_salesman_optimization.empirical_analysis` recebe um ou
mais CSVs e produz `enriched_results.csv` e `summary.json`. São calculados:

- razão de aspecto do bounding box;
- proporção de vértices extremos no fecho convexo;
- entropia espacial normalizada em grade `ceil(sqrt(n))`;
- grau máximo da AGM determinística;
- coeficiente de variação das distâncias ao vizinho mais próximo;
- quantidade e proporção de violações da desigualdade triangular na matriz
  `EUC_2D` efetivamente usada.

O resumo contém regressões log-log de tempo e memória, R², RMSE, regressão
múltipla do tempo e agregados por warm-start. Timeouts são dados censurados e
excluídos dos ajustes de complexidade. Gaps só usam ótimo certificado na mesma
instância ou fornecido por SHA-256 em `--known-optima-json`.

`peak_memory_bytes` é o high-water mark do processo worker inteiro, sempre em
bytes. No Windows, a origem é `GetProcessMemoryInfo.PeakWorkingSetSize`; em
Linux e macOS é `getrusage(RUSAGE_SELF).ru_maxrss`, com a unidade da plataforma
normalizada. Se nenhuma API estiver disponível, o fallback explicitamente
identificado mede apenas o pico de alocações Python com `tracemalloc`. O método
efetivo fica em `memory_measurement_method`. A medida inclui interpretador,
instância, matriz, busca e persistência; um processo morto externamente conserva
o pico observado até o último checkpoint.

## Custo da instrumentação

Há custo constante de leituras do relógio por chamada instrumentada e por
ponto de verificação, além da consulta de memória e da escrita atômica em cada
checkpoint. O custo de persistência aparece em `checkpoint_seconds`, mas, por
ser síncrono, também aumenta busca e total do solver. O intervalo padrão de 30
segundos mantém esse efeito pequeno em buscas longas. Processos isolados têm
custo de startup, visível apenas em `executor_wall_seconds`. A instrumentação
v5 preserva a fila best-first e o limite das duas arestas, mas altera a regra de
poda e a geração efetivamente enfileirada ao acrescentar dominância e descarte
antes da heap; por isso, comparações históricas devem observar a versão e a
impressão digital registradas.

## Validação curta

Os testes automatizados cobrem ótimo, rota/custo, timeout parcial, retomada,
reexecução sem duplicata e continuação depois de erro:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Um smoke test manual, sem disparar o lote completo:

```powershell
.\scripts\run_experiments.bat data\instances\example_crossing.tsp `
  --output-dir experiments\results\smoke --timeout-seconds 5

.\scripts\run_experiments.bat data\instances\example_crossing.tsp `
  --output-dir experiments\results\smoke-timeout --timeout-seconds 0
```
