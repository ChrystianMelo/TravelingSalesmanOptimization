# Análise do baseline experimental: inicialização trivial

Este documento registra o lote já coletado para o Branch-and-Bound best-first
com inicialização trivial. Ele é um retrato dos dados de
[`experiments/results/trivial/results.csv`](../../experiments/results/trivial/results.csv),
e não substitui o CSV nem os registros JSON de cada execução.

## Identificação do lote

| Campo | Valor |
|---|---|
| Configuração | `dbca7761a482aa53` |
| Invocação | `20261118T150714.235462Z-8d7fe9dc` |
| Algoritmo | `branch_and_bound_best_first` |
| Inicialização | rota trivial, na ordem dos vértices |
| Repetições | 1 por instância |
| Limite do solver | 1.800 s por execução |
| Checkpoints | a cada 30 s |
| Tolerância externa | 10 s |
| Período | 18/11/2026, de 12:07 a 15:33 (BRT, UTC-3) |
| Ambiente | Windows 11, CPython 3.12.7, AMD64, 8 CPUs lógicas |
| Processador registrado | Intel64 Family 6 Model 140 Stepping 2 |
| Commit | `e802da6e9ecc305c5ca76560d009022ad8404ca8` |
| Estado do repositório | `dirty` |
| Esquema/instrumentação | versão 1 / versão 1 |

O comando registrado foi equivalente a:

```powershell
.\.venv\Scripts\python.exe -m traveling_salesman_optimization.experiment_runner `
  data\instances --output-dir experiments\results\trivial
```

O registro original da invocação contém o caminho absoluto, o tamanho e o
SHA-256 de cada arquivo de instância. O `run_id` de cada linha também depende
do conteúdo da instância e dos parâmetros relevantes da execução.

## Cobertura das instâncias

O lote contém 16 execuções com dimensões entre 4 e 70:

- 12 subinstâncias derivadas de instâncias da TSPLIB por
  `random.Random(seed)`; a origem, a semente e os IDs sorteados estão nos
  comentários de cada arquivo `.tsp`;
- 3 instâncias completas da TSPLIB: `berlin52`, `eil51` e `st70`;
- 1 instância sintética de validação, `example_crossing`.

Treze das 16 entradas (81,25%) têm no máximo 40 vértices. Desconsiderando a
instância sintética, são 12 de 15 (80%). A instância `example_crossing` é útil
para validar o executor, mas deve ser excluída dos ajustes estatísticos finais.

## Resultados consolidados

Os tempos abaixo são `solver_total_seconds`; a memória é o pico do processo
worker inteiro, convertido de bytes para MiB. `Melhor` é a melhor rota viável
preservada e não implica otimalidade quando o status é `timeout`.

| Instância | n | Status | Inicial | Melhor | Ótimo | Solver (s) | Expandidos | Podados | Pico (MiB) |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|
| `example_crossing` | 4 | `optimal` | 48 | 40 | 40 | 0,004 | 5 | 4 | 19,1 |
| `sub_eil101_10_seed101` | 10 | `optimal` | 350 | 233 | 233 | 0,014 | 65 | 285 | 19,1 |
| `sub_kroA100_10_seed102` | 10 | `optimal` | 24.637 | 9.070 | 9.070 | 0,036 | 78 | 368 | 19,1 |
| `sub_kroB100_15_seed201` | 15 | `optimal` | 19.373 | 10.213 | 10.213 | 1,778 | 4.477 | 31.945 | 29,9 |
| `sub_rd100_15_seed202` | 15 | `optimal` | 7.634 | 3.509 | 3.509 | 0,118 | 110 | 772 | 19,3 |
| `sub_pr107_20_seed301` | 20 | `optimal` | 94.909 | 29.538 | 29.538 | 0,784 | 533 | 7.107 | 21,3 |
| `sub_rat99_20_seed302` | 20 | `optimal` | 1.716 | 557 | 557 | 5,461 | 5.421 | 65.984 | 40,7 |
| `sub_bier127_25_seed402` | 25 | `timeout` | 142.963 | 142.963 | `NA` | 1.798,063 | 3.696.150 | 0 | 9.538,2 |
| `sub_lin105_25_seed401` | 25 | `optimal` | 34.995 | 9.408 | 9.408 | 1.310,230 | 1.220.480 | 17.065.393 | 5.955,9 |
| `sub_a280_30_seed501` | 30 | `optimal` | 3.500 | 957 | 957 | 1,931 | 2.373 | 49.886 | 36,6 |
| `sub_pr124_30_seed502` | 30 | `optimal` | 205.697 | 41.385 | 41.385 | 167,757 | 150.075 | 2.226.335 | 851,5 |
| `sub_ch130_35_seed601` | 35 | `timeout` | 12.871 | 12.871 | `NA` | 1.793,296 | 1.986.779 | 0 | 8.781,5 |
| `sub_gil262_35_seed602` | 35 | `timeout` | 3.015 | 3.015 | `NA` | 1.800,000 | 468.910 | 0 | 3.986,2 |
| `eil51` | 51 | `timeout` | 1.308 | 1.308 | `NA` | 1.800,000 | 470.190 | 0 | 6.160,6 |
| `berlin52` | 52 | `timeout` | 22.205 | 22.205 | `NA` | 1.775,440 | 763.922 | 0 | 8.731,9 |
| `st70` | 70 | `timeout` | 3.410 | 3.410 | `NA` | 1.800,000 | 367.354 | 0 | 7.396,9 |

Resumo do lote:

- 10 resultados `optimal` (62,5%) e 6 `timeout` (37,5%);
- nenhuma execução terminou com `error`;
- 3,404 h acumuladas dentro do solver e 3,429 h de tempo de parede do
  executor;
- 9.136.922 estados expandidos e 19.448.079 estados podados;
- maior pico de memória: 9.538,2 MiB (9,315 GiB), em
  `sub_bier127_25_seed402`;
- execução ótima mais demorada: `sub_lin105_25_seed401`, com 1.310,230 s
  (aproximadamente 21 min 50 s).

## Leitura preliminar

### Limite superior trivial

Nas dez execuções concluídas, a redução entre a rota inicial e a rota ótima
variou de 16,7% (`example_crossing`) a 79,9% (`sub_pr124_30_seed502`). Nas seis
execuções interrompidas, a melhor rota registrada ainda era a rota trivial e
nenhum estado havia sido podado. Esses dados são compatíveis com um limite
superior inicial fraco, mas a comparação causal exige executar as demais
estratégias sobre as mesmas instâncias.

### Dimensão não explica o custo sozinha

O comportamento não foi monotônico em função de `n`. Por exemplo,
`sub_a280_30_seed501` foi resolvida em 1,931 s e 36,6 MiB, enquanto
`sub_bier127_25_seed402`, com cinco vértices a menos, atingiu o prazo e 9,315
GiB. A `sub_lin105_25_seed401` terminou, mas consumiu 1.310,230 s e 5,816 GiB.
Isso reforça a necessidade de relacionar o desempenho às características
geométricas das instâncias, e não apenas à dimensão.

### Limite inferior e AGM são gargalos

Somadas todas as execuções, o cálculo do limite inferior ocupou 11.195,925 s,
ou 91,36% do tempo de busca. As consultas à árvore geradora mínima (AGM), que
estão contidas nesse tempo, ocuparam 5.639,261 s, ou 46,02% da busca. Houve
204.243.111 consultas de AGM, das quais 191.483.127 foram hits de cache
(93,75%).

No subconjunto que atingiu o prazo, o limite inferior representou 94,08% da
busca e as consultas de AGM, 49,86%. Esses percentuais identificam as rotinas
prioritárias para profiling detalhado; eles não devem ser somados porque o
tempo de AGM já está contido no tempo do limite inferior.

### Memória da busca best-first

Seis execuções ultrapassaram 5 GiB de pico, e cinco delas atingiram o prazo.
A medida inclui todo o processo worker — interpretador, instância, matriz de
distâncias, fronteira da busca e persistência —, portanto não isola a fila de
prioridade. Ainda assim, os picos indicam que o consumo de memória da fronteira
best-first precisa ser acompanhado nas próximas estratégias.

## Semântica dos timeouts

`optimal_cost=NA` significa que a busca não provou a otimalidade. A coluna
`best_route_cost` continua registrando uma solução viável, que neste lote
coincidiu com a rota inicial nos seis timeouts.

Três timeouts foram cooperativos (`eil51`, `sub_gil262_35_seed602` e `st70`).
Os outros três (`berlin52`, `sub_bier127_25_seed402` e
`sub_ch130_35_seed601`) exigiram encerramento externo após a tolerância de 10
s. Nesses casos, o tempo e os contadores do solver vêm do último checkpoint
válido e podem ficar abaixo de 1.800 s; o tempo de parede do executor inclui a
espera e o encerramento do processo.

## Limitações deste lote

- Há apenas uma repetição por instância; ainda não é possível estimar
  variabilidade nem intervalos de confiança.
- Somente a inicialização trivial foi avaliada. Não há comparação de
  warm-start nem resultados de Twice-around-the-tree ou Christofides.
- O checkout estava `dirty` e `PYTHONHASHSEED` não estava definido. O hash dos
  arquivos de entrada está registrado, mas a reprodução exata também depende
  de preservar as alterações locais que existiam no momento do lote.
- O pico de memória é específico do método `Windows GetProcessMemoryInfo
  PeakWorkingSetSize`; comparações com outros sistemas devem respeitar a
  diferença de método.
- As características geométricas das instâncias ainda não foram calculadas;
  por isso não há regressão de complexidade nem análise de sensibilidade.
- Os JSON, logs, rotas e checkpoints estão ignorados pelo Git na configuração
  atual. O CSV é rastreável, mas os artefatos auxiliares precisam ser
  preservados separadamente ou incluídos na política de versionamento antes da
  entrega final.

## Próximas coletas necessárias

Para completar a avaliação, deve-se repetir o mesmo painel de instâncias com
Vizinho Mais Próximo, inserção gulosa pelo fecho convexo,
Twice-around-the-tree e Christofides. As execuções devem manter o mesmo limite,
instrumentação e ambiente, usar múltiplas repetições quando houver variação de
tempo relevante e acrescentar as características geométricas exigidas para a
modelagem de sensibilidade.
