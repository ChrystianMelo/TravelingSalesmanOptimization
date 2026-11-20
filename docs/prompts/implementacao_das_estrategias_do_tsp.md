# Condução da implementação, revisão e auditoria das estratégias do TSP

## Contexto e objetivo consolidado

Depois de definir a infraestrutura inicial, conduzi a evolução do repositório
até uma implementação funcional, testável e reproduzível do TSP geométrico.
Delimitei como escopo o Branch-and-Bound exato, as cinco formas de inicializar
seu limite superior e os algoritmos aproximativos Twice-around-the-tree e
Christofides.

Antes de autorizar a implementação, determinei a leitura do enunciado
`docs/assignment/tp2.pdf`, a inspeção da estrutura e das alterações já
existentes e o uso dos slides das aulas 11 a 15 como referência conceitual.
Mantive esses documentos como fontes técnicas a serem confrontadas com o
estado real do projeto, e não como substitutos das decisões registradas neste
histórico.

Também defini os critérios de entrega: integração com o executor de
experimentos, documentação no README e nos documentos técnicos, além de
docstrings para entradas, saídas, invariantes, complexidade e exceções
relevantes. Resultados experimentais só poderiam ser registrados depois de
efetivamente coletados.

## Método de acompanhamento que adotei

Adotei como regra inspecionar o estado efetivo do código, dos testes e da
documentação antes de cada intervenção. Para cada requisito relevante, cobrei
a identificação da estrutura de dados correspondente, dos invariantes que ela
deveria preservar, da evidência de teste e do impacto sobre o protocolo
experimental. Não considerei suficiente uma solução que apenas produzisse o
custo esperado em um exemplo isolado.

Quando uma decisão alterava a arquitetura — como substituir a pilha implícita
da recursão por uma fila de prioridade ou trocar a formulação do limite
inferior — exigi o registro da motivação, do efeito sobre os contadores e dos
testes de regressão correspondentes. Nas revisões, preservei os componentes já
conformes e limitei as correções às divergências demonstradas por código,
contraexemplo, teste ou requisito do enunciado.

## Leitura e representação das instâncias

Defini uma única representação compartilhada das instâncias, para evitar que
cada algoritmo adotasse convenções próprias de índices, custos ou fechamento
de rota. Solicitei a leitura de instâncias TSPLIB do tipo `EUC_2D` com os
seguintes requisitos:

- preservar os IDs originais e a ordem dos vértices na seção
  `NODE_COORD_SECTION`;
- validar dimensão, IDs duplicados, presença das seções obrigatórias e tipo de
  peso aceito;
- usar internamente índices contíguos de `0` a `n - 1`, mantendo uma associação
  inequívoca com os IDs originais;
- construir uma única matriz simétrica de distâncias para ser compartilhada
  por todos os algoritmos;
- calcular cada peso `EUC_2D` pela regra da TSPLIB
  `int(hypot(dx, dy) + 0.5)`;
- centralizar o cálculo do custo de uma rota fechada, sem exigir que a origem
  seja repetida na representação interna;
- apresentar e persistir as rotas finais com os IDs originais, repetindo a
  origem quando o formato externo exigir um ciclo explicitamente fechado.

## Solver exato por Branch-and-Bound

Para o solver exato, determinei o uso de Branch-and-Bound no TSP simétrico. O
primeiro vértice deveria permanecer fixo como origem para eliminar ciclos
equivalentes por rotação. Cada estado deveria representar uma rota parcial,
seu custo acumulado, o último vértice visitado e o conjunto dos vértices ainda
não visitados.

A fronteira da busca deveria usar uma fila de prioridade e estratégia
best-first. O estado com menor limite inferior deveria ser escolhido entre
todos os estados ativos. Empates precisariam de um critério estável, como a
ordem de inserção, para tornar os experimentos reproduzíveis.

O solver deveria manter sempre uma rota hamiltoniana viável como incumbente.
O custo dessa rota seria o limite superior corrente. Um estado cujo limite
inferior fosse maior ou igual ao custo da incumbente poderia ser podado, pois
a busca procurava uma melhora estrita e já possuía uma rota com aquele custo.

O resultado deveria conter, no mínimo:

- melhor rota viável conhecida;
- custo dessa rota;
- custo da rota usada para inicializar o limite superior;
- status de otimalidade ou timeout;
- número de nós expandidos;
- número de nós podados;
- profundidade máxima observada;
- tempos de inicialização, busca e total;
- instrumentação das chamadas do limite inferior e dos checkpoints.

A semântica dos contadores deveria ser documentada com precisão. Um estado
parcial removido da fila e aprovado pelo teste do limite conta como expandido
quando seus filhos são gerados. Um estado rejeitado pelo limite conta como
podado. Uma folha completa pode atualizar a incumbente, mas não conta como
expandida, pois não gera descendentes.

## Revisão da ordem de exploração

Ao revisar a primeira versão, identifiquei que a fronteira da busca havia sido
implementada por recursão em profundidade. Comparei essa decisão com a
estratégia best-first discutida na Aula 12 e concluí que, embora a solução
ótima ainda pudesse ser encontrada, a arquitetura da busca não correspondia ao
critério que eu havia estabelecido.

Solicitei então a substituição da pilha implícita por uma fila de prioridade
capaz de comparar globalmente os limites de todos os estados ativos. Também
determinei a atualização dos testes e da documentação, pois essa mudança afeta
a quantidade e a sequência de nós expandidos e podados, mesmo quando o custo
ótimo permanece igual.

## Revisão do limite inferior

Na versão inicial, observei que o limite combinava o custo percorrido, a árvore
geradora mínima dos vértices restantes e as conexões da ponta atual e da
origem. Depois do primeiro lote experimental, reavaliei essa escolha à luz das
páginas 13 a 15 da Aula 12 e determinei sua substituição definitiva pelo
limite das duas arestas incidentes.

O novo limite deveria considerar que cada vértice de um ciclo hamiltoniano tem
grau dois e adaptar essa ideia aos estados de caminho da busca:

- as arestas já percorridas são obrigatórias;
- vértices internos da rota parcial já possuem grau dois;
- a origem e a ponta atual possuem uma aresta fixada e precisam de mais uma;
- vértices restantes precisam de duas arestas permitidas;
- ligações prematuras entre origem e ponta ou ligações com vértices internos
  não podem ser usadas para completar artificialmente o grau;
- a soma das contribuições incidentes deve ser dividida por dois, com o
  arredondamento seguro necessário para custos inteiros;
- folhas completas devem receber exatamente o custo do caminho mais a aresta
  de retorno à origem;
- instâncias degeneradas de um ou dois vértices devem continuar válidas.

Manter somente esse limite no solver e remover métricas legadas da AGM que não
representassem mais a implementação corrente. A configuração dos experimentos
deveria registrar explicitamente qual limite estava em uso.

## Interface substituível para o limite superior

Para impedir que o solver acumulasse condicionais específicos de cada
heurística, solicitei a separação entre a construção da rota inicial e a lógica
do Branch-and-Bound. Toda estratégia deveria obedecer ao mesmo contrato:
receber uma instância e retornar uma permutação de todos os índices internos,
sem repetir a origem no fim.

O solver deveria validar essa permutação, rotacionar o ciclo para iniciar no
índice zero quando necessário e calcular o custo pela função centralizada. Um
registro por nome deveria permitir selecionar a estratégia na CLI e no
executor sem inserir condicionais específicas dentro do solver ou do worker.

Implementar exatamente as cinco estratégias de inicialização solicitadas no
TP2.

## Estratégia 1: cold start trivial

Preservar a rota ingênua na ordem do arquivo:

```text
0 -> 1 -> 2 -> ... -> n - 1 -> 0
```

Internamente, retornar somente `(0, 1, ..., n - 1)`, pois o cálculo de custo
fecha o ciclo. Essa estratégia deveria continuar sendo o padrão e a referência
para medir o custo das heurísticas e o impacto delas sobre a poda.

## Estratégia 2: Vizinho Mais Próximo

Implementar a busca gulosa apresentada na Aula 13:

1. iniciar no vértice de índice zero;
2. enquanto existirem vértices não visitados, escolher o mais próximo do
   último vértice da rota;
3. resolver empates pela ordem dos índices internos;
4. retornar a permutação, deixando o fechamento do ciclo para a função de
   custo comum.

Documentar que essa heurística é simples e rápida, mas não possui a mesma
garantia constante das aproximações baseadas em AGM para o TSP métrico.

## Estratégia 3: fecho convexo com inserção gulosa

Construir primeiro uma sub-rota contendo os vértices extremos do conjunto de
pontos. O fecho convexo poderia ser implementado pela cadeia monotônica, com
ordenação por coordenadas e produto vetorial para remover giros incompatíveis.

Pontos colineares que não fossem extremos e vértices com coordenadas repetidas
não deveriam ser perdidos. Eles poderiam ficar fora da semente do fecho, mas
precisariam ser inseridos posteriormente, preservando cada índice exatamente
uma vez.

Depois de formar o ciclo inicial, inserir iterativamente os demais vértices.
Em cada rodada, avaliar todo par composto por um vértice restante `v` e uma
aresta consecutiva `(a, b)` do ciclo. O acréscimo de custo é:

```text
d(a, v) + d(v, b) - d(a, b)
```

Escolher globalmente a inserção de menor acréscimo. Em empates, usar primeiro
o índice do vértice e depois a posição da aresta, garantindo uma saída
determinística. Ao final, rotacionar a rota para o índice zero.

## Estratégia 4: Twice-around-the-tree

Implementar o algoritmo aproximativo estudado na Aula 13 e usar sua rota como
limite superior inicial:

1. calcular uma árvore geradora mínima do grafo completo;
2. considerar a duplicação de suas arestas, que produz um multigrafo
   euleriano;
3. percorrer esse multigrafo e eliminar repetições de vértices por atalhos;
4. retornar o ciclo hamiltoniano resultante.

Como a pré-ordem de uma AGM enraizada representa os mesmos atalhos da caminhada
euleriana da árvore duplicada, ela poderia ser usada diretamente. Implementar
a AGM por Prim denso, adequado ao grafo completo já armazenado em uma matriz
de custos. Definir desempates determinísticos na escolha do próximo vértice e
do pai.

Documentar que, sob custos métricos, o algoritmo possui fator de aproximação
2. A implementação deveria funcionar também para um ou dois vértices.

## Estratégia 5: Christofides

Implementar as quatro etapas apresentadas no material:

1. calcular uma AGM `T`;
2. obter o conjunto `I` dos vértices de grau ímpar em `T` e calcular um
   matching perfeito de peso mínimo no grafo completo induzido por `I`;
3. formar um multigrafo com as arestas da AGM e do matching e encontrar um
   circuito euleriano;
4. eliminar visitas repetidas por atalhos para obter uma rota hamiltoniana.

O matching deveria ser realmente perfeito e de peso mínimo. Uma solução por
programação dinâmica exponencial não seria apropriada para as instâncias de
até 75 vértices do trabalho. Como o enunciado permite bibliotecas de grafos
para suporte, usar o algoritmo Blossom disponibilizado pelo NetworkX e
declarar essa dependência no projeto.

Construir o circuito euleriano por Hierholzer. O multigrafo pode conter duas
arestas entre o mesmo par de vértices quando uma aresta pertence simultaneamente
à AGM e ao matching; portanto, usar identificadores próprios de aresta para
não confundir arestas paralelas. Depois, manter somente a primeira ocorrência
de cada vértice no circuito euleriano.

Validar que todos os vértices foram visitados e que o matching cobriu todo o
conjunto de graus ímpares. Documentar que, sob custos métricos, Christofides
possui fator de aproximação 1,5.

## Casos extremos e determinismo

Todas as cinco estratégias deveriam ser auditadas para:

- instância com um único vértice;
- instância com dois vértices;
- custos empatados;
- pontos colineares;
- coordenadas duplicadas com IDs diferentes;
- IDs TSPLIB fora de ordem ou não contíguos;
- arestas de custo zero produzidas pelo arredondamento `EUC_2D`;
- rotas determinísticas em execuções repetidas.

O solver deveria rejeitar qualquer estratégia que omitisse, repetisse ou
inventasse um índice.

## CLI e seleção das estratégias

A interface de linha de comando deveria aceitar o caminho de uma instância e
uma opção `--strategy`, com os nomes canônicos:

- `trivial`;
- `nearest_neighbor`;
- `convex_hull`;
- `twice_around_tree`;
- `christofides`.

O padrão deveria permanecer `trivial`. A saída deveria informar a estratégia
selecionada, o custo, a rota com IDs originais e os contadores principais do
Branch-and-Bound.

O executor de experimentos deveria usar o mesmo registro e persistir o nome da
estratégia na configuração e no CSV, permitindo comparar separadamente os cinco
warm-starts.

## Automação dos experimentos

Para que os resultados pudessem ser comparados e auditados, defini um executor
reproduzível para o Branch-and-Bound com os seguintes requisitos:

- aceitar arquivos `.tsp` e diretórios pesquisados recursivamente;
- executar cada par instância–repetição em um processo isolado;
- usar limite padrão de 1.800 segundos por execução;
- aplicar primeiro um timeout cooperativo no solver e manter uma margem antes
  de `terminate` ou `kill` como salvaguarda externa;
- preservar a melhor incumbente, os contadores e os tempos parciais quando a
  busca expirar;
- diferenciar `optimal`, `timeout` e `error`;
- preencher o custo ótimo somente quando a prova de otimalidade estiver
  concluída;
- salvar CSV consolidado, configuração canônica, especificação de cada
  execução, checkpoints, resultado detalhado, rota TSPLIB TOUR e log;
- usar escrita atômica para que uma interrupção não substitua o último arquivo
  válido por um arquivo parcial;
- permitir retomada sem duplicar resultados concluídos;
- fornecer `--rerun` para substituir explicitamente uma execução existente;
- calcular identificadores reproduzíveis a partir da configuração, caminho,
  hash da instância e repetição;
- registrar plataforma, Python, CPU e estado do Git;
- medir o pico de memória do processo e documentar o método usado em cada
  plataforma;
- medir com relógio monotônico e documentar quais tempos estão contidos em
  outros para evitar somas incorretas.

O tempo `initialization_seconds` deveria incluir toda a estratégia escolhida,
inclusive fecho convexo, AGM ou matching. Dessa forma, a comparação de
warm-start considera o custo de obter uma incumbente melhor, e não apenas a
redução posterior na árvore de busca.

## Testes obrigatórios

Não tratei a implementação como concluída apenas porque as rotas pareciam
plausíveis. Determinei a criação de testes unitários e de integração que
cobrissem:

- parser TSPLIB e regra de arredondamento `EUC_2D`;
- custo centralizado de ciclos;
- comparação do Branch-and-Bound com força bruta em instâncias pequenas;
- uma instância em que a rota trivial contenha cruzamentos e não seja ótima;
- admissibilidade do limite inferior em rotas parciais pequenas;
- preservação dos IDs originais;
- validação e substituição da estratégia inicial;
- timeout zero preservando a incumbente;
- semântica de tempos e contadores;
- presença de exatamente cinco estratégias no registro;
- validade da permutação produzida por cada estratégia;
- desempate do Vizinho Mais Próximo;
- fecho convexo com ponto interno, ponto colinear e coordenada duplicada;
- custo da AGM e otimalidade de um matching pequeno conhecido;
- limites de Twice-around-the-tree e Christofides contra o ótimo por força
  bruta em uma instância métrica pequena;
- aceitação de todas as estratégias pela CLI e pelo executor;
- retomada, reexecução sem duplicatas, persistência da rota e continuação do
  lote depois de uma falha individual.

Executar a suíte completa, Ruff, verificação de formatação e
`git diff --check`. Também realizar um smoke test das cinco estratégias em uma
instância TSPLIB real sem iniciar uma busca exata longa desnecessária.

## Documentação e argumentação técnica

Solicitei que o README, a documentação do executor e o relatório explicassem
as escolhas que afetam o comportamento estrutural e empírico dos algoritmos,
em vez de apenas enumerar funções implementadas. Entre os pontos que mantive
sob revisão estavam:

- a diferença entre controlar a fronteira por DFS e por best-first;
- a admissibilidade do limite das duas arestas em rotas parciais;
- a relação entre pré-ordem, caminhada da árvore duplicada e shortcuts;
- o papel dos vértices de grau ímpar, do matching e do circuito euleriano;
- a dependência das garantias 2 e 1,5 em relação à desigualdade triangular;
- a inadequação de um matching exponencial para a escala das instâncias;
- a diferença entre custo inicial, incumbente e ótimo comprovado;
- a semântica e o custo das métricas usadas nos experimentos.

Mantive o histórico em `docs/prompts` como parte da rastreabilidade do
trabalho. As decisões centrais deveriam aparecer acompanhadas das revisões,
das correções exigidas e das evidências usadas para aceitá-las.

## Auditoria de conformidade da implementação

### Escopo e autorização

Quando a implementação ficou funcional, iniciei uma auditoria específica em
relação ao TP2. Delimitei a análise à correção matemática, Branch-and-Bound,
limite inferior da Aula 12, Twice-around-the-tree, Christofides, cinco
warm-starts, TSPLIB, instrumentação, protocolo experimental, sensibilidade,
testes e entregáveis.

Separei essa auditoria em duas etapas. Primeiro, determinei uma inspeção
somente leitura, com evidências, contraexemplos e recomendações, sem modificar
o projeto. Somente depois de avaliar o diagnóstico autorizei a correção dos
itens comprovadamente não conformes. Preservei os componentes aprovados e
mantive a proibição de iniciar a bateria completa de execuções de 30 minutos.

### Diagnóstico que orientou as correções

Na leitura das evidências, confirmei que não havia erro matemático crítico nos
três algoritmos. Por isso, mantive o Branch-and-Bound best-first, o limite das
duas arestas, a AGM, o matching perfeito mínimo, os multigrafos, os circuitos
eulerianos, os shortcuts e as cinco rotas iniciais.

Concentrei as correções nas lacunas comprovadas:

- ausência de profiling individual de AGM, matching, Euler e shortcut;
- ausência de um contador explícito de nós gerados;
- identidade experimental sem impressão digital do código e das dependências;
- comparação dos cinco warm-starts dependente de comandos manuais separados;
- timeout externo sem encerramento explícito da árvore de processos;
- possível divergência entre o último checkpoint JSON e o arquivo TOUR;
- ausência das características geométricas, auditoria da desigualdade
  triangular, gaps seguros e modelos com R²/RMSE;
- documentação incompleta da semântica dessas métricas.

Também considerei a evidência de que o arredondamento `EUC_2D` viola a
desigualdade triangular na maioria das instâncias locais. Mantive as rotas e a
exatidão do Branch-and-Bound, mas determinei que os fatores 2 e 1,5 não fossem
afirmados incondicionalmente sobre a matriz arredondada.

### Correções de instrumentação sem alteração algorítmica

Autorizei a criação de um coletor contextual de fases sem reescrever os
algoritmos já validados. As funções existentes de Prim,
Blossom, Hierholzer e shortcut continuaram com os mesmos contratos e decisões,
mas passaram a registrar chamadas, tempo monotônico e o pico residente do
processo observado ao final de cada fase. O high-water mark foi documentado
como memória do worker, não como memória exclusiva ou aditiva da subrotina.

O resultado do solver e o schema experimental passaram a incluir
`generated_nodes` e as métricas de AGM, matching, circuito euleriano e
shortcut. A raiz e cada filho cujo bound foi calculado contam como gerados;
folhas completas podem não ser expandidas nem podadas.

### Integridade e comparabilidade dos experimentos

O schema foi elevado para a versão 4. O `config_id` passou a incorporar:

- SHA-256 dos fontes Python relevantes e do `pyproject.toml`;
- versão e implementação do Python;
- plataforma e arquitetura;
- versões do NetworkX e do próprio pacote.

Assim, uma alteração efetiva da implementação ou do runtime cria outra
configuração e não é retomada silenciosamente como se fosse equivalente.

O executor passou a aceitar `--all-strategies` ou múltiplas ocorrências de
`--strategy`. Uma única invocação pode executar o mesmo painel com as cinco
inicializações, mantendo um `config_id` por estratégia e um CSV comum.

O prazo por execução passou a começar antes da leitura da instância. O tempo
já gasto é descontado antes da chamada do solver. Workers são criados em grupo
próprio e o timeout externo sinaliza a árvore do processo. A rota passou a
integrar o checkpoint JSON; o arquivo TOUR é rematerializado desse mesmo
retrato antes da consolidação do resultado.

### Análise de sensibilidade e qualidade

Foi adicionado um comando de análise que recebe um ou mais CSVs e produz
tabela enriquecida e resumo JSON. Ele calcula:

- razão de aspecto do bounding box;
- proporção de extremos no fecho convexo;
- entropia espacial normalizada;
- grau máximo da AGM;
- coeficiente de variação do vizinho mais próximo;
- quantidade e proporção de violações triangulares.

O resumo inclui regressões log-log de tempo e memória, regressão múltipla do
tempo, R², RMSE e agregados por warm-start. Timeouts são tratados como dados
censurados. Um gap só usa ótimo certificado em outra execução com o mesmo
SHA-256 ou um mapa externo explicitamente indexado por SHA-256; incumbentes de
timeout nunca são usadas como ótimo.

### Documentação e validação finais

README, documentação experimental e fonte LaTeX foram atualizados com a nova
semântica, comandos, limitações de memória e ressalva métrica. Foram
adicionados testes para profiling das aproximações, nós gerados, impressão
digital da configuração, execução conjunta das cinco estratégias,
características geométricas, violações triangulares e uso seguro de ótimos.

Não foram alterados o limite inferior, a ordem best-first, as regras de poda,
Prim, o matching, Hierholzer, o shortcut ou as cinco heurísticas. Não foram
gerados resultados longos nem conclusões experimentais artificiais.

### Verificações executadas

Para encerrar a etapa, exigi verificações proporcionais às mudanças realizadas:

- Ruff foi executado sobre `src`, `tests` e `scripts`, sem falhas;
- a suíte terminou com `25 passed`;
- `git diff --check` não encontrou erros de whitespace;
- um smoke test executou as cinco estratégias em uma única invocação sobre
  `example_crossing`, e as cinco terminaram com custo ótimo 40;
- o analisador processou esse CSV conjunto e reconheceu um grupo pareado com
  as cinco estratégias;
- o analisador também processou as 16 linhas históricas sem alterar a base,
  encontrando 14 instâncias com violações triangulares e ajustando o modelo de
  tempo apenas sobre as 10 execuções certificadas como ótimas;
- os diagramas de arquitetura foram regenerados e o relatório LaTeX compilou
  em um PDF de seis páginas.

Os resultados desses smoke tests ficaram em `.tmp/` e não devem ser usados
como base científica do TP. A bateria schema 4 com as instâncias e repetições
finais continua sendo uma etapa experimental deliberadamente não iniciada
nesta correção.

## Restrições de execução

Durante toda a condução, mantive os seguintes limites:

- preservar alterações locais preexistentes que não pertencessem ao escopo;
- não apagar resultados ou instâncias existentes;
- não criar commits automaticamente;
- não declarar resultados experimentais não executados;
- não iniciar lotes de 30 minutos apenas para validar a integração;
- manter o código compatível com Python 3.12 e com os scripts existentes do
  projeto.
