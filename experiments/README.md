# Executor de experimentos

O lote já coletado para a inicialização trivial, com configuração, tabela de
resultados, interpretação preliminar e limitações, está documentado em
[`docs/analysis/trivial-baseline.md`](../docs/analysis/trivial-baseline.md).
A adaptação e o piloto do limite das duas arestas estão em
[`docs/analysis/lower-bound-two-edges.md`](../docs/analysis/lower-bound-two-edges.md).

O módulo `traveling_salesman_optimization.experiment_runner` executa o
Branch-and-Bound sequencialmente, com um processo novo para cada par
instância–repetição. A única estratégia registrada nesta etapa é `trivial`;
novas estratégias entram no registro `INITIAL_ROUTE_STRATEGIES` e usam a mesma
interface do solver e do executor.

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
  --strategy trivial --lower-bound mst --repetitions 3 `
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

`--lower-bound mst` seleciona o limite original baseado em AGM e é o padrão;
`--lower-bound two_edges` seleciona o limite das duas arestas incidentes. A
opção integra a configuração canônica e, portanto, altera `config_id` e
`run_id`. A coluna `lower_bound_strategy` também identifica a escolha no CSV e
nos registros. O schema 2 acrescentou essa coluna; resultados do schema 1
continuam intactos, mas uma nova execução deve usar outra pasta de saída (ou um
CSV previamente migrado).

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
- `mst_seconds` mede todas as consultas de AGM, inclusive lookup no cache, e
  está contido em `lower_bound_seconds` e em `search_seconds`;
- `checkpoint_seconds` está contido em `search_seconds`;
- `executor_wall_seconds` inclui inicialização do interpretador, leitura da
  instância, solver, serialização e encerramento do processo. Ele não é um
  componente de `solver_total_seconds`.

Portanto, tempos de limite inferior, AGM e checkpoint não devem ser somados ao
tempo de busca. `lower_bound_calls` conta chamadas iniciadas;
`mst_calls = mst_computations + mst_cache_hits`. Uma computação interrompida
pelo prazo ainda conta como chamada/computação e conserva o tempo já gasto.
Com `two_edges`, `mst_calls`, `mst_computations`, `mst_cache_hits` e
`mst_seconds` permanecem zero; as chamadas e todo o custo do novo cálculo são
mantidos em `lower_bound_calls` e `lower_bound_seconds`.

Cada estado removido da fila incrementa no máximo um dos contadores:
`expanded_nodes` quando gera filhos e `pruned_nodes` quando seu limite é maior
ou igual à incumbente. Folhas viáveis não são expansões. `max_depth` é o maior
número de arestas escolhidas depois da origem (raiz zero, ciclo completo
`n - 1`).

`initial_route_cost` é o limite superior inicial; `best_route_cost` é sempre o
custo da melhor rota preservada. `optimal_cost` só recebe esse custo em
`status=optimal`; em `timeout` e `error`, recebe o literal `NA`, como exige o
enunciado. O worker recalcula o custo da rota antes de aceitar um resultado
final.

## Prazo, checkpoint e memória

O prazo do solver cobre inicialização mais busca. O solver o verifica
cooperativamente no laço da busca, na geração de filhos e no Prim. Ao expirar,
devolve `timeout` com a incumbente, contadores e tempos parciais. O executor
espera ainda `--external-grace-seconds` (10 por padrão) e então usa
`terminate`/`kill` como salvaguarda, convertendo o último checkpoint válido em
resultado de timeout.

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
custo de startup, visível apenas em `executor_wall_seconds`. A ordem da fila, o
limite, a regra de poda e a geração dos filhos não foram alterados.

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
