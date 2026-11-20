# Análise piloto do limite inferior das duas arestas

## Definição e adaptação

A definição foi conferida nas páginas 13–15 de
`aula12-branch-and-bound.pdf`, disponibilizado nos slides da aula 12. O limite
soma, para cada vértice, as duas arestas incidentes que ainda podem ocupar seu
grau no circuito, divide a soma por dois porque cada aresta aparece nas duas
pontas e aplica teto aos custos inteiros:

```text
LB = ceil(soma das contribuições dos vértices / 2)
```

O solver representa um estado por uma rota simples iniciada no vértice de
índice zero, sua ponta atual, os vértices restantes e o custo das arestas já
percorridas. A adaptação usa as seguintes permissões:

- na raiz, cada vértice contribui com suas duas arestas incidentes distintas
  mais baratas;
- as arestas da rota parcial são obrigatórias; um vértice interno já possui as
  duas arestas fixadas e não aceita outra ligação;
- quando ainda há vértices restantes, a origem e a ponta atual possuem uma
  aresta fixa cada e escolhem a outra somente entre os vértices restantes. A
  aresta entre as duas pontas fica proibida para não fechar um subciclo antes
  da hora;
- um vértice restante pode escolher arestas para outro vértice restante, para
  a origem ou para a ponta atual, mas não para um vértice interno da rota;
- se faltarem arestas distintas permitidas para completar o grau de algum
  vértice, o estado é inviável e pode ser podado;
- uma rota completa recebe seu custo exato, incluindo a volta à origem.

Na implementação, `2 * cost_so_far` é a contribuição conjunta das arestas
fixas nas suas duas pontas. Somam-se apenas as contribuições ainda ausentes e
aplica-se `(soma + 1) // 2`; `cost_so_far` não é adicionado outra vez. Para
preservar a semântica já testada do projeto em uma instância degenerada de dois
vértices, a única ida e volta é tratada exatamente, pois um grafo simples com
dois vértices não oferece duas arestas incidentes distintas.

O argumento `--lower-bound` aceita `mst` (padrão e implementação anterior) ou
`two_edges`. A busca continua best-first, os filhos continuam sendo gerados na
ordem crescente dos índices e não houve mudança na inicialização, na regra de
poda, nos checkpoints ou no prazo. `lower_bound_calls` e
`lower_bound_seconds` continuam medindo o LB escolhido. As métricas `mst_*`
ficam zeradas quando a AGM não é usada.

## Validação curta

Os dois limites são executados nos mesmos testes pequenos e comparados com a
solução por força bruta. Para `two_edges`, prefixos de diferentes profundidades
também são comparados com a melhor conclusão por força bruta: o limite não pode
excedê-la. Há verificações específicas do custo exato de uma rota completa, do
caso de dois vértices, da instrumentação e da identidade de retomada no
executor.

## Instância escolhida

O primeiro piloto usa `sub_gil262_35_seed602`. As duas candidatas prioritárias
têm 35 vértices e ambas consumiram o prazo de 1.800 s com o LB por AGM, de modo
que os tempos registrados e a quantidade de nós processados não demonstram
qual seria mais barata. O critério operacional disponível foi o pico observado
de memória: aproximadamente 4,18 GB em `sub_gil262_35_seed602`, contra 9,21 GB
em `sub_ch130_35_seed601`; a primeira também encerrou cooperativamente, enquanto
a segunda precisou da salvaguarda externa.

Essa escolha não prevê qual LB será melhor. Existe apenas uma repetição, o pico
mede o worker inteiro e a mudança do limite altera prioridades, podas e tamanho
da fronteira. O critério apenas reduz o risco esperado do primeiro ensaio entre
duas instâncias da mesma dimensão.

## Comando do piloto

No Windows PowerShell, a execução isolada fica preparada como:

```powershell
.\scripts\run_experiments.bat data\instances\sub_gil262_35_seed602.tsp `
  --output-dir experiments\results\lb_two_edges_pilot `
  --strategy trivial --lower-bound two_edges `
  --repetitions 1 --timeout-seconds 1800 `
  --checkpoint-interval-seconds 30 --external-grace-seconds 10
```

A pasta é diferente de `experiments/results/trivial`, e
`lower_bound_strategy` participa da configuração canônica que gera
`config_id` e `run_id`. Assim, a retomada não confunde o piloto com o timeout
anterior nem sobrescreve seus CSV, JSON, logs, checkpoints ou rotas. O comando
não foi executado durante esta alteração.

Devem ser comparados com a linha anterior: `status` (principalmente se concluiu
dentro do prazo), `solver_total_seconds`, `expanded_nodes`,
`lower_bound_seconds` e `best_route_cost`. `lower_bound_calls` e as métricas de
memória ajudam a interpretar o perfil. Se ambos terminarem em timeout, a
quantidade de nós processados isoladamente não define um vencedor: limites com
custos por chamada e ordens de expansão diferentes podem produzir vazões muito
diferentes sem provar a solução.
