# TravelingSalesmanOptimization

TravelingSalesmanOptimization é o repositório do Trabalho Prático 2 de DCC207 —
Algoritmos 2 da Universidade Federal de Minas Gerais (UFMG). O trabalho aborda
a implementação, a auditoria, a análise empírica e a otimização de algoritmos
exatos e aproximativos para o Problema do Caixeiro Viajante (TSP) geométrico.

O [enunciado do TP2](docs/assignment/tp2.pdf) está disponível neste repositório.

> **Estado atual:** leitura TSPLIB `EUC_2D`, Branch-and-Bound exato best-first,
> cold start trivial, instrumentação por subrotina e executor reproduzível com
> timeout, checkpoints, retomada e processos isolados. As demais estratégias de
> warm-start e os algoritmos aproximativos entram pela interface já preparada.

## Objetivos

O trabalho deve investigar o desempenho teórico e prático das soluções, com
ênfase nas estruturas de dados, nos gargalos computacionais, na modelagem
empírica de complexidade, na eficiência das podas e na influência das
características geométricas e topológicas das instâncias sobre as soluções
exatas e aproximadas.

## Algoritmos exigidos

O enunciado exige três algoritmos para o TSP:

- algoritmo exato baseado em Branch-and-Bound;
- algoritmo aproximativo Twice-around-the-tree;
- algoritmo aproximativo de Christofides.

O Branch-and-Bound deve ser avaliado com cinco estratégias de inicialização do
limite superior:

1. inicialização trivial (cold start) com a rota `1 -> 2 -> ... -> n -> 1`;
2. Vizinho Mais Próximo (Nearest Neighbor);
3. inserção gulosa iniciada pelo fecho convexo;
4. Twice-around-the-tree;
5. Christofides.

## Avaliação experimental

Cada execução terá o limite de 30 minutos. Execuções interrompidas por tempo
devem ser registradas como `NA`, preservando os contadores coletados até a
interrupção. A avaliação deve incluir:

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

## Instâncias de teste

Os experimentos devem utilizar de 12 a 16 instâncias `EUC_2D` da TSPLIB, com 10
a 75 vértices. Aproximadamente 80% das instâncias selecionadas devem ter no
máximo 40 vértices. A faixa de 45 a 75 vértices será usada para testes de
estresse, nos quais o algoritmo exato poderá exceder o limite de tempo enquanto
os algoritmos aproximativos deverão permanecer viáveis. O enunciado sugere
instâncias como `ulysses16`, `gr24`, `fri26`, `bays29`, `swiss42` e `att48`.

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

O trabalho pode ser desenvolvido por grupos de até três estudantes. Ferramentas
de IA generativa são permitidas, mas seu uso deve ser documentado, e o grupo
deve compreender, auditar criticamente e defender tecnicamente a implementação
entregue.

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
.\scripts\run.bat data\instances\example_crossing.tsp
```

No Linux ou macOS:

```bash
python scripts/tasks.py run data/instances/example_crossing.tsp
```

A rota exibida usa os IDs originais e repete a origem no final. O custo de
toda rota inclui essa aresta de retorno.

### Automação dos experimentos

O executor aceita arquivos `.tsp` e/ou pastas, usa 1.800 segundos por execução
por padrão e salva um CSV depois de cada processo isolado:

```powershell
.\scripts\run_experiments.bat data\instances `
  --output-dir experiments\results\trivial --repetitions 3
```

Executar novamente o mesmo comando retoma o lote e pula resultados `optimal`
ou `timeout`; `--rerun` força a repetição sem criar linha duplicada. A descrição
dos tempos, memória, status, arquivos e comandos de validação está em
[experiments/README.md](experiments/README.md).

### Contadores do Branch-and-Bound

Cada estado visitado incrementa exatamente um contador:

- `nós podados` aumenta quando o limite inferior do estado é maior ou igual ao
  custo da melhor rota conhecida; seus descendentes não são gerados;
- `nós expandidos` aumenta quando um estado parcial passa pelo teste do limite
  e seus filhos são gerados. Uma folha completa que melhora a solução é
  avaliada, mas não é expandida, pois não possui filhos.

O estado inicial também segue essas regras. A igualdade pode ser podada porque
já existe uma rota incumbente com o mesmo custo, e a busca procura uma melhora.

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

## Relatório e entregáveis

A entrega final deve incluir todos os arquivos-fonte, a base de métricas
coletadas — tempos, memória, características das instâncias e estatísticas de
poda — e o relatório científico em PDF e em código-fonte LaTeX. O relatório
deve seguir o formato de artigo da SBC e conter introdução; implementação,
profiling e auditoria; experimentos e resultados modelados; e conclusões.

A discussão da implementação deve justificar as estruturas de dados e a
estratégia de exploração da árvore, documentar refatorações críticas de código
produzido com auxílio de IA e explicar como o profiling identificou subrotinas
caras e problemas de memória. Caso LLMs sejam utilizadas, também é obrigatório
entregar um anexo com o histórico de prompts.

A entrega será feita por um repositório no GitHub. O prazo informado no
enunciado é **24 de novembro de 2026, às 23h59**, sem aceitação de trabalhos
atrasados.
