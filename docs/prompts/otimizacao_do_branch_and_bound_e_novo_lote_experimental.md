# Otimização do Branch-and-Bound e execução de um novo lote experimental

## Contexto da revisão

Depois do primeiro painel experimental, observei uma quantidade de timeouts
maior que a esperada para a faixa principal do TP2. Das 75 execuções
balanceadas, somente 25 terminaram com prova de otimalidade e 50 atingiram o
limite de 1.800 segundos. Os timeouts ocorreram sob todas as estratégias em dez
das 15 instâncias.

A análise do código indicou que as cinco estratégias de warm-start estavam
produzindo rotas válidas e que o principal gargalo estava na busca exata
compartilhada por elas. Mesmo uma incumbente próxima do ótimo não era
suficiente para evitar a construção de uma fronteira muito grande. A revisão
foi, portanto, direcionada à representação e à eliminação de estados do
Branch-and-Bound, sem substituir as cinco estratégias exigidas e sem alterar o
limite inferior das duas arestas.

## Mudanças solicitadas

Autorizei três mudanças na implementação, preservando a exatidão do algoritmo,
a política best-first e o critério de poda por limite inferior.

### 1. Dominância de estados equivalentes

Um estado passou a ser identificado pelo par:

```text
(vértice atual, conjunto de vértices ainda não visitados)
```

Dois prefixos que chegam ao mesmo par possuem exatamente o mesmo conjunto de
continuações possíveis. Se um deles tem custo parcial maior ou igual ao outro,
ele não pode produzir um ciclo melhor e pode ser descartado com segurança.

Foi adicionada uma tabela `best_state_cost` que mantém o menor custo parcial
conhecido para cada estado. Um filho dominado é rejeitado antes da chamada do
limite inferior. Como um caminho mais barato pode ser descoberto depois que
uma entrada já foi inserida na heap, o solver também verifica, ao removê-la,
se ela se tornou obsoleta.

Essa mudança reduz a repetição de trabalho causada pelas diferentes
permutações de um mesmo conjunto visitado. Ela não transforma o solver em uma
heurística: somente estados comprovadamente dominados por outro prefixo com as
mesmas continuações são eliminados.

### 2. Poda antes da inserção na heap

Na implementação anterior, todo filho tinha seu limite calculado, sua rota
copiada e sua entrada inserida na heap, inclusive quando
`child_bound >= best_cost`. O estado só seria contabilizado como podado quando
fosse removido da fila.

O teste do limite passou a ocorrer antes de `heappush`. Estados que já não
podem melhorar a incumbente são contabilizados como podados e não ocupam a
fronteira. Além disso, se o menor limite retirado da heap já for maior ou igual
à incumbente, todos os estados restantes também são podáveis e a prova pode
ser encerrada sem removê-los individualmente.

Essa alteração preserva a ordem dos estados realmente exploráveis, mas reduz
operações de heap e retenção desnecessária de memória.

### 3. Compartilhamento estrutural dos prefixos de rota

Cada entrada da heap armazenava uma tupla com toda a rota parcial. A expressão
`partial_route + (next_vertex,)` criava uma nova cópia de tamanho proporcional
à profundidade para cada filho. Como a busca mantinha milhões de estados
simultaneamente, essas cópias contribuíam para o pico de memória e para a
paginação do processo.

A rota parcial passou a ser representada por um nó imutável contendo somente:

- o último vértice;
- uma referência para o nó pai;
- a profundidade.

Irmãos compartilham o mesmo prefixo, e a rota completa só é materializada
quando uma folha melhora a incumbente. A mudança reduz o espaço por estado sem
alterar os custos, limites ou decisões da busca.

## Instrumentação e validação

Como a dominância e a poda antecipada alteram a semântica dos contadores, a
versão da instrumentação foi elevada para 5. A interpretação corrente é:

- `generated_nodes` conta a raiz e cada filho considerado;
- `pruned_nodes` inclui poda por limite, dominância e estados remanescentes
  eliminados quando o menor limite da heap já prova que não há melhora;
- `lower_bound_calls` pode ser menor que `generated_nodes`, pois um estado
  dominado é descartado antes do cálculo do limite;
- `expanded_nodes` continua contando estados aprovados que efetivamente geram
  filhos.

Foi acrescentado um teste que compara o resultado com força bruta e confirma
que estados equivalentes piores são rejeitados antes do limite inferior. A
validação da alteração terminou com:

- 26 testes aprovados;
- Ruff sem falhas;
- verificação de formatação aprovada;
- `git diff --check` sem erros de whitespace.

Como ensaio curto, `sub_pr107_20_seed301`, que anteriormente atingia o limite
de 1.800 segundos, terminou com ótimo comprovado em aproximadamente 16,2
segundos usando o warm-start por fecho convexo. Esse ensaio serviu somente como
evidência inicial; a avaliação científica exigiu a repetição do painel
completo.

## Necessidade de novos experimentos

Os resultados anteriores não poderiam ser reutilizados para avaliar a nova
implementação. As três mudanças alteram a quantidade de limites calculados, a
semântica da poda, o tamanho da fronteira e os tempos de execução. Além disso,
o executor inclui a impressão digital dos fontes no `config_id`, fazendo com
que a implementação otimizada constitua uma nova configuração experimental.

Determinei, portanto, um novo lote em diretório separado, sem apagar ou
misturar o painel anterior. O protocolo foi mantido:

- 15 instâncias de 10 a 70 vértices;
- cinco estratégias de warm-start;
- uma repetição balanceada por combinação;
- 75 execuções no total;
- limite de 1.800 segundos por execução;
- checkpoint a cada 30 segundos;
- margem externa de dez segundos.

O comando utilizado foi equivalente a:

```powershell
$instances = Get-ChildItem data\instances -Filter *.tsp |
    Where-Object { $_.Name -ne "example_crossing.tsp" } |
    ForEach-Object { $_.FullName }

.\scripts\run_experiments.bat $instances `
    --output-dir experiments\results\optimized-v5 `
    --all-strategies `
    --repetitions 1 `
    --timeout-seconds 1800 `
    --checkpoint-interval-seconds 30 `
    --external-grace-seconds 10
```

Depois da coleta, a análise foi regenerada a partir do novo CSV:

```powershell
.\.venv\Scripts\python.exe scripts\tasks.py analysis `
    experiments\results\optimized-v5\results.csv `
    --output-dir experiments\results\optimized-v5\analysis
```

## Resultado do novo lote

O novo painel foi efetivamente executado e concluído. As 75 execuções foram
iniciadas em 23 de novembro de 2026 às 11h58 e terminaram em 24 de novembro de
2026 às 1h35, no horário de Brasília, totalizando aproximadamente 13 horas e
37 minutos de coleta sequencial.

| Estratégia | Execuções | Ótimos comprovados | Timeouts |
|---|---:|---:|---:|
| Christofides | 15 | 10 | 5 |
| Fecho convexo | 15 | 11 | 4 |
| Vizinho Mais Próximo | 15 | 11 | 4 |
| Trivial | 15 | 11 | 4 |
| Twice-around-the-tree | 15 | 11 | 4 |
| **Total** | **75** | **54** | **21** |

No painel anterior, havia 25 execuções ótimas e 50 timeouts. Com a
implementação otimizada, foram observadas 54 provas de otimalidade e 21
timeouts sob o mesmo tamanho de painel e o mesmo prazo por execução. Assim, o
novo lote produziu 29 conclusões adicionais dentro do limite.

Os artefatos foram preservados em:

- `experiments/results/optimized-v5/results.csv`;
- `experiments/results/optimized-v5/runs/`;
- `experiments/results/optimized-v5/checkpoints/`;
- `experiments/results/optimized-v5/logs/`;
- `experiments/results/optimized-v5/analysis/`.

## Limitações da comparação

Apesar da melhora observada, 21 execuções ainda atingiram o prazo, sobretudo
nas instâncias maiores. O Branch-and-Bound continua exponencial, e as mudanças
reduzem redundância e memória sem eliminar o colapso nas instâncias de
estresse.

Também há somente uma repetição por combinação. Por isso, os tempos absolutos
continuam sujeitos à carga do sistema, paginação e outras condições do
ambiente. A comparação mais segura é a mudança no número de execuções que
conseguiram concluir a prova dentro do mesmo limite.

Por fim, os contadores do painel antigo e do novo não devem ser agregados em
uma mesma regressão: a versão 5 contabiliza dominância e poda antecipada de
forma diferente. O relatório, as tabelas e os modelos posteriores devem usar
o painel `optimized-v5` como uma nova base experimental claramente
identificada.

## Restrições mantidas

Durante essa etapa, mantive as seguintes decisões:

- não remover nem substituir nenhuma das cinco estratégias obrigatórias;
- não substituir o Branch-and-Bound por outro solver exato;
- não alterar o limite inferior das duas arestas neste lote;
- não misturar resultados de implementações com impressões digitais distintas;
- não apresentar incumbentes de timeout como soluções ótimas;
- não criar commits automaticamente.
