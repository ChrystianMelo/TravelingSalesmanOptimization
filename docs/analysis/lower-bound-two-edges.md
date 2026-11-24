# Análise do piloto do limite inferior das duas arestas

Este documento registra a introdução do limite inferior das duas arestas e o
primeiro ensaio realizado com ele. Trata-se de um registro histórico da etapa
inicial: os painéis intermediário e final, descritos na documentação principal,
usam o mesmo limitante com instrumentação e regras de poda posteriores.

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

Esse é o único limite inferior mantido no solver atual. Na alteração avaliada
por este piloto, a busca continuou best-first, os filhos continuaram sendo
gerados na ordem crescente dos índices e não houve mudança simultânea na
inicialização, na regra de poda, nos checkpoints ou no prazo. As otimizações
posteriores de dominância e poda antes da heap pertencem à etapa final.
`lower_bound_calls` e `lower_bound_seconds` medem as chamadas do limitante e seu
tempo acumulado.

## Validação curta

O limite é executado nos testes pequenos existentes e comparado com a solução
por força bruta. Prefixos de diferentes profundidades também são comparados
com a melhor conclusão por força bruta: o limite não pode excedê-la. Há
verificações específicas do custo exato de uma rota completa, do caso de dois
vértices, da instrumentação e da retomada no executor.

## Contexto da avaliação

O primeiro piloto do novo limite foi executado e permanece preservado na etapa
inicial. Ele compara uma única execução com o baseline anterior baseado em AGM,
na mesma instância e com inicialização trivial. O ensaio serviu para verificar o
comportamento operacional do limitante, não para estimar ganho estatístico ou
declarar superioridade entre as formulações.

## Instância escolhida

O primeiro piloto usou `sub_gil262_35_seed602`. As duas candidatas prioritárias
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

## Piloto preservado

O piloto foi incorporado à etapa inicial e seu CSV permanece em
[`experiments/results/initial/lb_two_edges_pilot/results.csv`](../../experiments/results/initial/lb_two_edges_pilot/results.csv).
O comando equivalente no layout atual é:

```powershell
.\scripts\run_experiments.bat data\instances\sub_gil262_35_seed602.tsp `
  --output-dir experiments\results\initial\lb_two_edges_pilot `
  --strategy trivial `
  --repetitions 1 --timeout-seconds 1800 `
  --checkpoint-interval-seconds 30 --external-grace-seconds 10
```

A pasta é diferente dos painéis intermediário e final, e a configuração
canônica registra `lower_bound: "two_edges"`. Os identificadores e metadados
originais foram preservados mesmo após a reorganização dos diretórios.

## Resultado do piloto

A linha de referência está em
[`experiments/results/initial/trivial/results.csv`](../../experiments/results/initial/trivial/results.csv).
Os dois ensaios usaram a mesma instância, uma repetição, rota inicial trivial e
prazo de 1.800 segundos:

| Métrica | LB baseado em AGM | LB das duas arestas |
|---|---:|---:|
| Status | `timeout` | `timeout` |
| Encerramento | cooperativo | externo por `terminate` |
| Tempo interno preservado (s) | 1.800,000 | 1.777,115 |
| Tempo de parede do executor (s) | 1.809,483 | 1.810,030 |
| Estados expandidos | 468.910 | 903.140 |
| Estados podados | 0 | 0 |
| Chamadas do limite | 11.604.258 | 20.626.874 |
| Tempo acumulado no limite (s) | 1.723,314 | 1.482,369 |
| Melhor custo preservado | 3.015 | 3.015 |
| Pico residente (GB decimais) | 4,18 | 7,32 |

O limite das duas arestas permitiu processar mais estados e acumulou menos tempo
dentro da rotina de limite durante a janela observada, mas isso não produziu
uma prova nem melhorou a incumbente. Seu pico residente foi maior, e o
encerramento externo fez o tempo interno refletir o último checkpoint válido,
não todo o intervalo de parede. Como ambos terminaram em `timeout`, a quantidade
de nós processados isoladamente não define um vencedor: limites com custos por
chamada e ordens de expansão diferentes podem produzir vazões distintas sem
provar a solução. A evidência mais ampla sobre o limitante vem dos painéis
intermediário e final, e não deste ensaio único.
