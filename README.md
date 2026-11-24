# TravelingSalesmanOptimization

TravelingSalesmanOptimization é o repositório do Trabalho Prático 2 de DCC207 —
Algoritmos 2 da Universidade Federal de Minas Gerais (UFMG). O trabalho aborda
a implementação, a auditoria, a análise empírica e a otimização de algoritmos
exatos e aproximativos para o Problema do Caixeiro Viajante (TSP) geométrico.

## Documentação oficial

O artigo em [`docs/report/main.tex`](docs/report/main.tex) é a síntese
científica da entrega, não a documentação canônica de uso ou implementação. As
referências oficiais do projeto são:

- este README, para instalação, execução e visão geral;
- [arquitetura e fluxos](docs/architecture.md), para módulos, contratos e
  diagramas;
- [estratégias de warm-start](docs/implementation/warm-start-strategies.md),
  para os algoritmos e suas complexidades;
- [executor de experimentos](experiments/README.md), para protocolo, schema,
  métricas, timeout e artefatos;
- [`docs/analysis/`](docs/analysis/), para registros técnicos intermediários;
- [histórico consolidado de uso de IA](docs/prompts/historico.md),
  para decisões, correções, contribuições assistidas e resultados.

O [PDF do artigo](docs/report/main.pdf) apresenta a análise e as conclusões do
painel coletado. Em caso de divergência operacional, prevalecem o código, os
testes e os documentos técnicos acima.

## Objetivos

O trabalho investigou o desempenho teórico e prático das soluções, com
ênfase nas estruturas de dados, nos gargalos computacionais, na modelagem
empírica de complexidade, na eficiência das podas e na influência das
características geométricas e topológicas das instâncias sobre as soluções
exatas e aproximadas.

## Algoritmos exigidos

O enunciado exige três algoritmos para o TSP:

- algoritmo exato baseado em Branch-and-Bound;
- algoritmo aproximativo Twice-around-the-tree;
- algoritmo aproximativo de Christofides.

O Branch-and-Bound foi avaliado com cinco estratégias de inicialização do
limite superior:

1. inicialização trivial (cold start) com a rota `1 -> 2 -> ... -> n -> 1`;
2. Vizinho Mais Próximo (Nearest Neighbor);
3. inserção gulosa iniciada pelo fecho convexo;
4. Twice-around-the-tree;
5. Christofides.

A implementação, as complexidades, os critérios de desempate, as garantias e
os casos degenerados estão documentados em
[Estratégias de warm-start](docs/implementation/warm-start-strategies.md).

## Arquitetura e diagramas

A documentação de [arquitetura e fluxos dos algoritmos](docs/architecture.md)
reúne um fluxo geral dos experimentos, um grafo de chamadas Code2flow separado
para cada estratégia, UML de classes e módulos gerado com Pyreverse e o fluxo
do Branch-and-Bound. Ela também descreve como regenerar os artefatos após
alterações em `src/`.

## Avaliação experimental

Cada execução do painel recebeu o limite de 30 minutos. Execuções interrompidas
por tempo são registradas como `NA` nos campos que exigem conclusão, preservando
a incumbente e os contadores coletados até a interrupção. A avaliação inclui:

- profiling de tempo e memória por subrotina, incluindo os gargalos da árvore
  geradora mínima e do emparelhamento perfeito quando bibliotecas de grafos
  forem utilizadas;
- modelos de regressão para as complexidades empíricas de tempo e espaço, com
  métricas de ajuste como R² ou RMSE;
- contagem de nós expandidos e podados pelo Branch-and-Bound para cada
  estratégia de warm-start, considerando também o custo da heurística inicial;
- gaps de aproximação e análise de sensibilidade a características como razão
  de aspecto do bounding box, proporção de pontos no fecho convexo, entropia ou
  densidade de agrupamento espacial, grau máximo na árvore geradora mínima e
  coeficiente de variação das distâncias ao vizinho mais próximo;
- um modelo de sensibilidade, como árvore de decisão ou regressão múltipla, que
  relacione as características das instâncias ao desempenho dos algoritmos e à
  qualidade das soluções.

### Evolução dos resultados

Os resultados preservam três etapas da evolução do trabalho:

| Etapa | Diretório | Papel na evolução |
|---|---|---|
| Inicial | [`initial`](experiments/results/initial/) | Primeiros experimentos com a implementação de referência, incluindo o baseline trivial e o piloto do limite das duas arestas. |
| Intermediária | [`intermediate`](experiments/results/intermediate/) | Cinco warm-starts, instrumentação ampliada e evidência dos gargalos de tempo, fronteira e memória. |
| Final | [`final`](experiments/results/final/) | Branch-and-Bound após dominância de estados, poda antes da heap e compartilhamento dos prefixos de rota. |

A etapa inicial não forma um painel diretamente comparável às seguintes,
porque usa schemas anteriores e se concentra no baseline trivial. O CSV da
etapa intermediária acumula 96 linhas; a comparação histórica seleciona as 75
células correspondentes ao mesmo painel da etapa final por SHA-256 da
instância, estratégia e repetição. Os identificadores técnicos dos CSVs foram
preservados para garantir a rastreabilidade.

O painel balanceado da versão final contém 75 execuções: 15 instâncias, cinco
estratégias, uma repetição e limite de 1.800 segundos. Os dados estão em
[`results.csv`](experiments/results/final/results.csv), e a tabela com features,
referências e gaps está em
[`enriched_results.csv`](experiments/results/final/analysis/enriched_results.csv).

- 54 execuções (72%) provaram a otimalidade e 21 atingiram timeout;
- a etapa intermediária provava 25 das mesmas 75 células;
- dez instâncias foram resolvidas pelas cinco estratégias e uma décima primeira
  por quatro delas;
- o fecho convexo produziu a melhor rota inicial nas 15 instâncias e gap médio
  de 2,15% nas 14 com ótimo de referência;
- como solvers independentes, Christofides produziu rota de menor custo que
  Twice-around-the-tree nas 15 comparações, com gaps médios de 9,25% e 26,45%;
- o maior pico residente foi 11,38 GiB, portanto a pressão de memória continua
  sendo uma limitação.

Os números são descritivos: existe apenas uma repetição por célula, 21 tempos
são censurados e os valores absolutos dependem da máquina e da carga do sistema.

## Instâncias de teste

O painel contém 15 instâncias `EUC_2D` da TSPLIB, com 10 a 70 vértices. Doze
possuem no máximo 40 vértices e três pertencem à faixa de estresse de 45 a 75.
Doze entradas são subamostras reprodutíveis de instâncias maiores e três são
instâncias completas. A instância sintética `example_crossing`, com quatro
vértices, é usada somente em testes e não integra o painel científico.

Essa composição foi respaldada por esclarecimento do professor no fórum da
disciplina, em 24 de novembro de 2026, de que qualquer instância cuja função de
custo seja uma distância poderia ser usada. A origem, a semente, os IDs
selecionados e o hash de cada entrada derivada preservam a rastreabilidade; a
metodologia completa está descrita no
[protocolo experimental](experiments/README.md#base-experimental).

As instâncias estão disponíveis no
[repositório da TSPLIB](https://comopt.ifi.uni-heidelberg.de/software/TSPLIB95/)
e no [índice de instâncias TSP](https://comopt.ifi.uni-heidelberg.de/software/TSPLIB95/tsp/tspindex.html).

## Requisitos

- Python 3.12 ou superior neste projeto; o enunciado permite Python 3,
  preferencialmente, ou C++11;
- biblioteca padrão e, quando forem necessárias ao desenvolvimento, NumPy,
  SciPy, scikit-learn e Pandas;
- NetworkX ou igraph apenas como bibliotecas de apoio, com profiling dos
  gargalos computacionais em nível de subrotina.

Este trabalho foi desenvolvido individualmente por Chrystian Melo
(`chrystian1@ufmg.br`). O uso de ferramentas de IA generativa, permitido pelo
enunciado, foi documentado no
[`histórico consolidado`](docs/prompts/historico.md); as decisões e
saídas foram auditadas por testes, revisão do código e análise experimental.

## Instalação

No Windows PowerShell:

```powershell
.\scripts\config.bat
```

No Linux ou macOS:

```bash
python -m venv .venv
source .venv/bin/activate
python scripts/tasks.py setup
```

## Execução

O solver recebe o caminho de uma instância `.tsp`. No Windows PowerShell:

```powershell
.\scripts\run.bat data\instances\example_crossing.tsp `
  --strategy christofides
```

No Linux ou macOS:

```bash
python scripts/tasks.py run data/instances/example_crossing.tsp \
  --strategy christofides
```

A rota exibida usa os IDs originais e repete a origem no final. O custo de
toda rota inclui essa aresta de retorno. `--strategy` aceita `trivial`,
`nearest_neighbor`, `convex_hull`, `twice_around_tree` ou `christofides` e usa
`trivial` por padrão.

### Automação dos experimentos

O executor aceita arquivos `.tsp` e/ou pastas, usa 1.800 segundos por execução
por padrão e salva um CSV depois de cada processo isolado:

```powershell
.\scripts\run_experiments.bat data\instances `
  --output-dir experiments\results\christofides `
  --strategy christofides --repetitions 3
```

Para iniciar um novo lote com as cinco estratégias sobre o mesmo painel e na
mesma invocação:

```powershell
.\scripts\run_experiments.bat data\instances `
  --output-dir experiments\results\reproduction `
  --all-strategies --repetitions 3
```

Depois da coleta, as características geométricas, gaps e modelos estatísticos
podem ser gerados sem reexecutar os algoritmos. O comando abaixo reproduz a
análise do painel final usado no relatório:

```powershell
.\.venv\Scripts\python.exe scripts\tasks.py analysis `
  experiments\results\final\results.csv `
  --output-dir experiments\results\final\analysis `
  --known-optima-json experiments\known_optima.json
```

O analisador nunca usa a incumbente de um timeout como ótimo. Ótimos externos
só são aceitos por um mapa JSON indexado pelo SHA-256 da instância.

Executar novamente o comando de experimentos retoma o lote e pula resultados
`optimal` ou `timeout`; `--rerun` força a repetição sem criar linha duplicada.
A descrição dos tempos, memória, status, arquivos e comandos de validação está em
[experiments/README.md](experiments/README.md).

### Contadores do Branch-and-Bound

Os contadores possuem as seguintes definições:

- `nós gerados` conta a raiz e cada filho considerado, inclusive filhos
  dominados antes do cálculo do limite inferior;

- `nós podados` inclui estados descartados pelo limite inferior, por dominância
  de um prefixo de custo menor ou igual que alcança o mesmo estado e, ao
  concluir a prova, a fronteira restante cujo menor limite já não melhora a
  incumbente;

- `nós expandidos` aumenta quando um estado parcial é retirado da fila e gera
  filhos. Uma folha completa é avaliada, mas não é expandida.

O estado inicial também segue essas regras. A igualdade pode ser podada porque
já existe uma rota incumbente com o mesmo custo, e a busca procura uma melhora.
Como a dominância pode agir antes do limite, `lower_bound_calls` pode ser menor
que `generated_nodes`; `gerados` também não é, em geral, a soma de `expandidos`
e `podados`.

## Testes e qualidade do código

No Windows PowerShell:

```powershell
.\scripts\run_tests.bat
.\.venv\Scripts\python.exe scripts\tasks.py check
```

No Linux ou macOS:

```bash
python scripts/tasks.py test
python scripts/tasks.py check
```

As mesmas verificações de código e os testes são executados automaticamente em
pushes e pull requests.

## Estrutura do projeto

```text
.
├── .github/workflows/       # Integração contínua
├── data/
│   └── instances/           # Instâncias selecionadas da TSPLIB
├── docs/
│   ├── assignment/          # Enunciado do trabalho
│   ├── analysis/            # Baselines e análises técnicas intermediárias
│   ├── diagrams/            # Diagramas de arquitetura gerados
│   ├── implementation/      # Decisões e detalhes dos algoritmos
│   ├── prompts/             # Histórico obrigatório de prompts de IA
│   └── report/              # Relatório SBC em LaTeX e figuras
├── experiments/
│   ├── scenarios/           # Definições reproduzíveis dos experimentos
│   └── results/             # Métricas coletadas e resultados gerados
├── scripts/                 # Comandos locais de configuração, execução e testes
├── src/
│   └── traveling_salesman_optimization/
├── tests/
│   ├── fixtures/
│   ├── integration/
│   └── unit/
└── pyproject.toml
```

## Artigo científico e entregáveis

A entrega final reúne todos os arquivos-fonte, a base de métricas
coletadas — tempos, memória, características das instâncias e estatísticas de
poda — e o artigo científico em PDF e em código-fonte LaTeX. O artigo segue o
formato da SBC e contém introdução; implementação,
profiling e auditoria; experimentos e resultados modelados; e conclusões.

A discussão justifica as estruturas de dados e a estratégia de exploração da
árvore, documenta refatorações críticas do código produzido com auxílio de IA e
explica como o profiling identificou subrotinas caras e problemas de memória.
O histórico de prompts integra a documentação entregue.

O artigo está disponível em [`docs/report/main.pdf`](docs/report/main.pdf), com
fonte em [`docs/report/main.tex`](docs/report/main.tex). Ele registra a análise
científica da versão entregue; instruções operacionais e contratos técnicos
permanecem nos documentos oficiais listados no início deste README.

A entrega está finalizada e organizada neste repositório. O prazo informado no
enunciado é **24 de novembro de 2026, às 23h59**.
