# Executor de experimentos

Os resultados preservam três etapas da evolução técnica e experimental:

| Etapa | Diretório | Conteúdo |
|---|---|---|
| Inicial | [`results/initial/`](results/initial/) | Baseline trivial da implementação de referência e piloto do limite das duas arestas, ainda sob schemas anteriores. |
| Intermediária | [`results/intermediate/`](results/intermediate/) | Executor e profiling ampliados, cinco warm-starts e identificação dos gargalos que motivaram a refatoração. |
| Final | [`results/final/`](results/final/) | Painel balanceado após dominância de estados, poda antes da heap e compartilhamento dos prefixos de rota. |

O painel final contém 75 execuções e é a base principal do
[`relatório`](../docs/report/main.pdf). A etapa intermediária preserva 96 linhas
acumuladas; sua comparação com a etapa final usa as mesmas 75 células,
selecionadas por SHA-256 da instância, estratégia e repetição. A etapa inicial
é histórica e não é agregada diretamente às regressões posteriores, pois usa
outros schemas e não cobre o mesmo painel de estratégias.

O diretório auxiliar [`results/trivial/`](results/trivial/) conserva no ambiente
de trabalho os artefatos do primeiro lote trivial. No repositório versionado,
seu `results.csv` é a base rastreável; uma cópia histórica desse CSV permanece
em `results/initial/trivial/` para preservar a organização usada na evolução
do projeto. Os documentos
[`trivial-baseline.md`](../docs/analysis/trivial-baseline.md) e
[`lower-bound-two-edges.md`](../docs/analysis/lower-bound-two-edges.md)
registram as decisões dessa fase.

Os CSVs entregues preservam `run_id`, `config_id`, hashes e demais métricas
necessárias à rastreabilidade. Quando mantidos localmente, os JSONs históricos
de especificação, invocação e análise conservam também o `output_dir` absoluto
registrado na execução, inclusive os nomes anteriores dos diretórios. Esses
valores são proveniência imutável, não caminhos ativos; comandos e scripts
atuais usam `initial`, `intermediate` e `final`.

O módulo `traveling_salesman_optimization.experiment_runner` executa o
Branch-and-Bound sequencialmente, com um processo novo para cada par
instância–repetição. As cinco estratégias registradas são `trivial`,
`nearest_neighbor`, `convex_hull`, `twice_around_tree` e `christofides`; todas
usam a mesma interface do solver e do executor.

## Base experimental

O painel científico contém 15 instâncias `EUC_2D` com 10 a 70 vértices: três
instâncias completas da TSPLIB (`eil51`, `berlin52` e `st70`) e doze
subinstâncias reprodutíveis derivadas das coordenadas de instâncias maiores da
mesma biblioteca. A complementação foi adotada porque havia disponibilidade
limitada de instâncias originais que atendessem simultaneamente à faixa
dimensional e à função de custo requeridas.

A metodologia foi descrita em uma pergunta no fórum da disciplina: derivar
novas entradas das coordenadas da TSPLIB, recalcular os custos conforme
`EUC_2D` e identificá-las separadamente. Em resposta publicada em 24 de
novembro de 2026, no tópico “Instâncias dos experimentos no TP2”, o professor
esclareceu:

> “Qualquer instância com função de custo que seja uma distância pode ser usada”.

O esclarecimento respalda a composição da base, mas não significa que uma
subinstância preserve a dificuldade ou o ótimo da origem. Por isso, cada
arquivo derivado registra instância de origem, semente e IDs selecionados em
seu cabeçalho; os resultados registram também o SHA-256 do arquivo efetivamente
executado.

## Comandos

No Windows PowerShell, o comando abaixo percorre todas as instâncias e usa os
padrões de uma repetição, 1.800 segundos por execução e estratégia `trivial`:

```powershell
.\scripts\run_experiments.bat data\instances `
  --output-dir experiments\results\example-run
```

Uma lista explícita, três repetições e checkpoints a cada 30 segundos:

```powershell
.\scripts\run_experiments.bat `
  data\instances\sub_eil101_10_seed101.tsp `
  data\instances\sub_kroA100_10_seed102.tsp `
  --output-dir experiments\results\example-selected `
  --strategy trivial --repetitions 3 `
  --timeout-seconds 1800 --checkpoint-interval-seconds 30
```

No Linux ou macOS, substitua o script por:

```bash
python scripts/tasks.py experiment data/instances \
  --output-dir experiments/results/example-run
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
schema, `instrumentation_version=5` é o identificador técnico da implementação
final: dominância de estados, poda antes da heap e contagem de todo filho
considerado como gerado.
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

Todos esses artefatos são produzidos no ambiente local. A política padrão do
`.gitignore` versiona os CSVs, inclusive `analysis/enriched_results.csv`, mas
ignora JSONs, logs, checkpoints, rotas e `analysis/summary.json`. Para arquivar
também esses auxiliares fora do ambiente de execução, é necessário incluí-los
deliberadamente no Git ou copiá-los para outro meio de preservação.

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
custo de startup, visível apenas em `executor_wall_seconds`. A implementação
final (`instrumentation_version=5`) preserva a fila best-first e o limite das
duas arestas, mas altera a regra de poda e a geração efetivamente enfileirada ao
acrescentar dominância e descarte antes da heap; por isso, comparações históricas
devem observar a etapa e a impressão digital registradas.

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
