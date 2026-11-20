# Estratégias de warm-start

O Branch-and-Bound recebe uma função que constrói uma rota hamiltoniana
viável. O custo dessa rota se torna a incumbente inicial (limite superior),
sem alterar o limite inferior nem a ordem best-first da busca exata. As cinco
estratégias pedidas no TP2 estão no registro `INITIAL_ROUTE_STRATEGIES`:

| Nome no executor | Estratégia | Tempo | Espaço auxiliar |
|---|---|---:|---:|
| `trivial` | ordem do arquivo | `O(n)` | `O(n)` para a rota |
| `nearest_neighbor` | Vizinho Mais Próximo | `O(n²)` | `O(n)` |
| `convex_hull` | fecho convexo + inserção mais barata | `O(n³)` | `O(n)` |
| `twice_around_tree` | AGM + Euler + atalhos | `O(n²)` | `O(n)` |
| `christofides` | AGM + matching + Euler + atalhos | `O(n² + k³)` | `O(n + k²)` |

Em Christofides, `k` é a quantidade (sempre par) de vértices de grau ímpar
na árvore geradora mínima. A parcela cúbica é o Blossom usado pelo NetworkX
para o emparelhamento perfeito de peso mínimo.

## Representação comum

Todas as estratégias retornam uma permutação dos índices internos
`0, ..., n - 1`, sem repetir a origem no fim. O solver valida a permutação,
rotaciona o ciclo para o índice zero quando necessário e calcula o custo pela
mesma matriz `EUC_2D` usada na busca. Apenas a apresentação e os arquivos
`.tour` convertem a rota para os IDs originais da TSPLIB.

Empates são resolvidos por índice e, quando aplicável, pela posição da aresta.
Essa regra torna repetíveis as rotas e os experimentos.

## Cold start / trivial

`trivial_initial_route` preserva exatamente a ordem das linhas da seção
`NODE_COORD_SECTION`. Ela é a referência sem custo heurístico relevante para
medir o impacto dos demais limites superiores sobre a poda.

## Vizinho Mais Próximo

`nearest_neighbor_initial_route` fixa o índice zero como origem. Enquanto
existirem vértices não visitados, escolhe o de menor custo a partir do último
vértice da rota. A heurística é rápida, mas não possui fator de aproximação
constante no caso geral discutido na Aula 13.

## Fecho convexo com inserção gulosa

`convex_hull_insertion_initial_route` calcula o fecho por cadeia monotônica em
`O(n log n)`. Os vértices extremos formam o ciclo inicial. A cada rodada, para
cada vértice restante `v` e aresta consecutiva `(a, b)`, calcula-se

```text
d(a, v) + d(v, b) - d(a, b).
```

O par com menor acréscimo é inserido. Avaliar todas as possibilidades em todas
as rodadas custa `O(n³)`, aceitável para a faixa de até 75 vértices do TP.
Pontos colineares não extremos e coordenadas repetidas ficam fora da semente,
mas entram normalmente durante a inserção, preservando cada ID uma vez.

## Twice-around-the-tree

`twice_around_tree_route` calcula uma AGM pelo Prim denso, adequado ao grafo
completo já representado por uma matriz. Suas arestas são duplicadas, o
multigrafo resultante é percorrido explicitamente por Hierholzer e as visitas
repetidas são eliminadas por atalhos. Sob a hipótese de custos métricos, a rota
custa no máximo duas vezes o ótimo.

## Christofides

`christofides_route` implementa as quatro etapas apresentadas na Aula 13:

1. calcula uma AGM por Prim;
2. encontra os vértices de grau ímpar e um matching perfeito de peso mínimo
   no grafo completo induzido por eles;
3. combina AGM e matching e encontra um circuito euleriano por Hierholzer;
4. ignora visitas repetidas, produzindo os atalhos do ciclo hamiltoniano.

O matching usa `networkx.algorithms.matching.min_weight_matching`, uma
implementação de Blossom para grafos gerais. IDs de aresta explícitos na etapa
de Hierholzer distinguem arestas paralelas quando AGM e matching contêm o
mesmo par. Christofides e Twice-around compartilham tanto a construção do
circuito euleriano quanto sua conversão por atalhos em uma rota hamiltoniana.
Sob custos métricos, a garantia de Christofides é de `1,5` vez o ótimo.

## Execução

Uma execução isolada pode selecionar a incumbente inicial:

```powershell
.\scripts\run.bat data\instances\example_crossing.tsp --strategy christofides
```

O executor de lotes aceita os mesmos cinco nomes:

```powershell
.\scripts\run_experiments.bat data\instances `
  --output-dir experiments\results\nearest-neighbor `
  --strategy nearest_neighbor --repetitions 3
```

O campo `initial_route_cost` permite comparar a qualidade do limite inicial;
`initialization_seconds` mede todo o custo da heurística, inclusive AGM e
matching. `expanded_nodes` e `pruned_nodes` medem o efeito posterior desse
limite na busca exata.

## Validação

Os testes exercitam nominalmente as cinco estratégias sobre a mesma instância
não trivial, validando a permutação e um custo esperado diferente para cada
uma. Testes adicionais se concentram nas estruturas críticas: custo da AGM,
otimalidade do matching e garantias aproximativas contra o ótimo de uma
instância pequena. A integração usa Christofides, a estratégia com o caminho de
execução mais complexo, enquanto o executor padrão cobre a rota trivial.
