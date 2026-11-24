# Histórico consolidado de uso de IA no TP2

## Nota de consolidação

Este documento consolida cronologicamente as interações que orientaram o desenvolvimento do TP2. As interações principais foram registradas e estão representadas pelos prompts principais destacados. Nem todos os prompts intermediários usados nos refinamentos permaneceram disponíveis; por isso, as solicitações complementares, revisões e resultados técnicos são apresentados de forma sintetizada, com base no histórico e nos artefatos preservados.

## 1. Configuração inicial do repositório — 11 de novembro de 2026

A primeira etapa delimitou a infraestrutura do projeto antes de qualquer implementação algorítmica. O repositório `DeliveryDispatch` foi indicado como referência de organização, enquanto o enunciado do TP2 permaneceu como fonte dos requisitos.

### Prompt principal

````text
Leia o arquivo tp2.pdf (enunciado do Trabalho Prático 2 de Algoritmos 2 da UFMG) e utilize o repositório https://github.com/ChrystianMelo/DeliveryDispatch como referência de organização, estilo e infraestrutura.

Prepare apenas a estrutura inicial deste novo projeto em Python, mantendo o mesmo padrão do DeliveryDispatch.

1. Crie um README.md em inglês, profissional e conciso, apresentando fielmente o enunciado do TP2, seus objetivos, algoritmos exigidos, estratégias de otimização, experimentos, entregáveis e requisitos. Utilize seções semelhantes às do DeliveryDispatch, sem apresentar funcionalidades futuras como já implementadas.

2. Organize o projeto com diretórios src/, tests/, data/, experiments/, docs/ e scripts/, incluindo subdivisões adequadas para instâncias, cenários experimentais, resultados e relatórios.

3. Configure pyproject.toml, .gitignore, .editorconfig, pytest e ruff, seguindo as convenções do projeto anterior.

4. Adicione somente um main.py que imprima "Hello, World!" e um teste pytest contendo assert 1 == 1.

5. Configure GitHub Actions (.github/workflows/ci.yml) para executar automaticamente lint e testes em push e pull requests.

6. Prepare uma estrutura inicial para o relatório em LaTeX, seguindo o formato SBC, sem desenvolver o conteúdo ou inventar resultados.

7. Inclua instruções simples de instalação, execução e testes no README.

Não implemente algoritmos, heurísticas, processamento de dados ou experimentos nesta etapa. O objetivo é exclusivamente preparar a infraestrutura para os primeiros commits.

Mantenha o projeto enxuto, organizado, modular e preparado para desenvolvimento incremental.

Ao final, execute os testes e o lint para verificar que tudo está funcionando.
````

### Desdobramentos consolidados

Interações posteriores ajustaram o idioma do README para português e colocaram o enunciado em `docs/assignment/`. A estrutura resultante reuniu `src/`, `tests/`, `data/`, `experiments/`, `docs/` e `scripts/`, a configuração do pacote, pytest, Ruff, EditorConfig, CI e o esqueleto SBC. O limite de escopo foi preservado: os algoritmos ainda não foram antecipados nessa etapa.

O resultado dessa fase foi uma base mínima executável e verificável. O [README](../../README.md) e o relatório foram ampliados somente nas etapas seguintes, depois que código e evidências passaram a existir.

## 2. Primeira implementação exata e correção da política de busca — 17 e 18 de novembro de 2026

A etapa seguinte introduziu a leitura de instâncias TSPLIB, a matriz de distâncias, o cálculo comum do custo dos ciclos e o Branch-and-Bound exato. A escolha inicial da busca em profundidade surgiu de uma discussão anterior com outro agente de IA, cuja sugestão foi incorporada ao pedido da primeira implementação, junto ao limite inferior baseado em árvore geradora mínima residual.

### Prompt principal

````text
Implemente a etapa 1 do TP2 de Algoritmos 2 da UFMG sobre o Problema do Caixeiro Viajante. Leia o enunciado em tp2.pdf e inspecione o repositório antes de editar. Aproveite o código existente e, se o projeto estiver vazio, use Python 3.

O objetivo desta etapa é ter um Branch-and-Bound exato e validado, com a rota trivial como solução inicial.

1. Implemente a leitura de instâncias TSPLIB do tipo EUC_2D. Preserve os IDs e a ordem dos vértices no arquivo e centralize o cálculo dos custos em uma matriz de distâncias. Use o arredondamento da TSPLIB, int(distância + 0.5), e uma função comum para calcular o custo de uma rota incluindo a volta à origem.

2. Implemente o Branch-and-Bound com busca em profundidade. Fixe o primeiro vértice como origem e inicialize o limite superior com o custo da rota na ordem do arquivo. Como limite inferior para uma rota parcial, use o custo já percorrido, somado ao custo da árvore geradora mínima dos vértices ainda não visitados, à menor aresta do vértice atual para esse conjunto e à menor aresta desse conjunto para a origem. Quando o conjunto estiver vazio, use o custo exato de fechar a rota.

3. Retorne a melhor rota, seu custo e as contagens de nós expandidos e podados. Documente exatamente quando cada contador aumenta. Mantenha a escolha da rota inicial separada da busca para que as outras estratégias de inicialização possam ser conectadas na etapa 2.

4. Crie uma forma simples de rodar o solver com um arquivo .tsp e valide a implementação comparando seu custo com força bruta em algumas instâncias pequenas. Inclua um caso em que a rota trivial seja pior que a ótima e confira que a rota retornada visita cada vértice uma única vez antes de voltar à origem. Execute os testes e mostre o resultado.

O escopo termina na leitura, nos custos, no Branch-and-Bound com rota trivial, nos contadores e na validação. Deixe as demais heurísticas, os experimentos e o relatório para as próximas etapas. Ao concluir, mostre o comando para executar o solver e explique brevemente por que o limite inferior permite podar sem perder o ótimo.
````

### Desdobramentos consolidados

A primeira formulação levou a uma implementação recursiva em profundidade. Durante a revisão, a sugestão recebida da IA foi reavaliada à luz do material da disciplina. Ao identificar que a DFS não era a política mais adequada à proposta do trabalho, foi solicitada sua substituição por *best-first search* com fila de prioridade. A fronteira passou a ser ordenada globalmente pelo menor limite inferior, com desempate estável, e os testes e a documentação foram ajustados à nova ordem de expansão e poda. Esse percurso registrou uma avaliação crítica da sugestão inicial, em vez de sua aceitação definitiva sem revisão.

A alteração preservou a exatidão, mas modificou a arquitetura e os contadores observados. O caso de teste disponível confirmou o mesmo custo ótimo sob as duas políticas, com contagens diferentes de nós; não foi executado um experimento controlado que permitisse atribuir à troca ganhos de tempo, memória ou redução geral da árvore de busca.

Ao final dessa etapa, o projeto possuía parser `EUC_2D`, arredondamento TSPLIB, matriz simétrica de custos, rota trivial separada da busca, Branch-and-Bound best-first, CLI e comparação com força bruta em instâncias pequenas. O limite baseado em AGM permaneceu apenas como decisão inicial: ele seria substituído na revisão seguinte.

## 3. Automação e rastreabilidade dos experimentos — 18 de novembro de 2026

Com o solver funcional, a próxima solicitação definiu um executor capaz de isolar processos, controlar o prazo, preservar resultados parciais e registrar métricas reproduzíveis.

### Prompt principal

````text
Automatize a execução e a coleta de resultados dos experimentos do Branch-and-Bound com inicialização trivial, aproveitando a implementação existente e as exigências do tp2.pdf.

Inspecione o repositório e implemente um executor de experimentos com as seguintes funcionalidades.

1. Configuração e execução
- Receber uma lista ou pasta de instâncias .tsp e uma pasta de saída.
- Permitir configurar o número de repetições e o limite de tempo, com padrão de 1.800 segundos por execução.
- Executar sequencialmente, em processos isolados, para evitar interferência entre experimentos e permitir interromper cada execução.
- Registrar a configuração utilizada e informações do ambiente para reprodução.

2. Coleta automática
Salvar uma linha por execução em CSV, contendo pelo menos:
- Instância, número de vértices, estratégia de inicialização e repetição.
- Custo da rota inicial e custo da melhor rota encontrada.
- Status da execução, distinguindo conclusão com ótimo comprovado, timeout e erro.
- Tempo de inicialização, tempo da busca e tempo total do solver.
- Nós expandidos, nós podados e profundidade máxima atingida.
- Pico de memória do processo, com unidade e método de medição documentados.
- Tempos e quantidades de chamadas das principais subrotinas existentes, incluindo cálculo do limite inferior e AGM, se utilizada.

Defina claramente o que cada tempo inclui. Caso uma medição contenha outra, documente essa relação para evitar somas incorretas. Use relógio monotônico para durações.

3. Limite de tempo e resultados parciais
- Ao atingir o limite, marcar o custo ótimo como NA e preservar a melhor solução viável encontrada, os contadores e os tempos parciais.
- Fazer o solver verificar o prazo e encerrar de forma cooperativa.
- Manter uma interrupção externa de segurança pelo executor caso o processo não encerre, preservando o último resultado parcial salvo.
- Salvar a rota correspondente à melhor solução em arquivo associado à execução.

4. Persistência e retomada
- Salvar os resultados após cada execução e checkpoints periódicos durante buscas longas.
- Permitir retomar um lote interrompido, pulando execuções já registradas como concluídas ou timeout na mesma configuração.
- Permitir repetir explicitamente execuções anteriores.
- Evitar linhas duplicadas e arquivos parcialmente gravados.
- Registrar falhas individuais e continuar o lote.

5. Validação
- Executar um lote pequeno para conferir a coleta e a retomada.
- Verificar um timeout com limite curto e conferir a preservação dos dados parciais.
- Conferir a consistência entre rota, custo e status.
- Mostrar os comandos para iniciar, retomar e repetir experimentos, além da localização e descrição dos arquivos gerados.

Nesta etapa, use a inicialização trivial já existente. Deixe o executor preparado para receber as demais estratégias pela mesma interface. Preserve a lógica de busca ao adicionar a instrumentação e explique o custo adicional das medições.

Implemente e valide a automação com execuções curtas. A execução do lote completo ficará para um comando manual.
````

### Desdobramentos consolidados

O executor resultante passou a persistir CSV, JSON, TOUR, logs e checkpoints, além de oferecer retomada, reexecução explícita, timeout cooperativo e salvaguarda externa. Nos refinamentos posteriores, foi solicitada uma indicação simples da porcentagem global de progresso no terminal, sem detalhamento de cada execução. As validações desta etapa permaneceram curtas; o lote completo foi reservado para execução manual posterior.

O protocolo resultante distinguiu incumbente de ótimo comprovado, usou `NA` quando o timeout impedia uma conclusão certificada e documentou a contenção entre tempos. Esse executor se tornou a base das etapas experimentais inicial, intermediária e final preservadas em `experiments/results/`.

## 4. Revisão e substituição do limite inferior — 19 e 20 de novembro de 2026

O primeiro lote motivou uma comparação entre o limite baseado em AGM e o limite das duas arestas incidentes apresentado na Aula 12. A solicitação preservava inicialmente os dois métodos e restringia a avaliação a validações curtas e a um único piloto preparado para execução separada.

### Prompt principal

````text
Quero testar o lower bound apresentado pelo professor na aula 12, comparando com o LB atual baseado em AGM. Inspecione o código e o executor de experimentos antes de editar.

1. Implementar o LB dos slides

Confira o arquivo aula12-branch-and-bound(1).pdf, especialmente as páginas 13–15, para confirmar a definição. Se o arquivo não estiver disponível, informe isso e use a descrição abaixo, deixando explícito que não conseguiu conferir o material.

O limite inferior considera que cada vértice precisa de exatamente duas arestas incidentes no circuito:

LB = ceil(soma das contribuições dos vértices / 2)

Para cada vértice:
- Nenhuma aresta fixada: contribuir com os custos das duas menores arestas incidentes distintas e permitidas.
- Uma aresta fixada: contribuir com seu custo e o da menor outra aresta permitida.
- Duas arestas fixadas: contribuir com os custos dessas duas arestas.

As arestas da rota parcial são obrigatórias. Respeite as restrições da busca ao definir as arestas permitidas. Se não houver arestas suficientes para completar o grau exigido, o estado é inviável.

A divisão por 2 corrige a contagem de cada aresta nas suas duas pontas. O teto se aplica aos custos inteiros usados no projeto. Essa fórmula já inclui as arestas da rota parcial: não some cost_so_far novamente.

Para uma rota completa, use seu custo exato, incluindo a volta à origem.

Mantenha o LB atual disponível e acrescente uma opção de configuração para escolher entre os dois. Preserve a estratégia de busca, a ordem de expansão, o warm-start e as demais condições experimentais.

2. Validar

Reaproveite os testes existentes e compare com força bruta em casos pequenos. Confira também que o novo LB nunca excede o custo da melhor conclusão de algumas rotas parciais pequenas.

Documente como o LB foi adaptado aos estados da implementação e mantenha sua instrumentação de tempo e chamadas.

3. Escolher um único caso para comparação

Estas cinco instâncias deram timeout com o LB atual:

- sub_ch130_35_seed601
- sub_gil262_35_seed602
- eil51
- berlin52
- st70

Inspecione os resultados e o profiling disponíveis e escolha um único caso para o primeiro teste. Priorize uma das duas instâncias de 35 vértices para reduzir o custo esperado. Como todas atingiram o timeout, não trate o tempo registrado como evidência de qual é mais barata. Explique brevemente a escolha e suas limitações.

4. Preparar uma execução separada

Ao concluir, forneça o comando exato, compatível com o executor existente, para repetir somente a instância escolhida usando o novo LB, com:
- A mesma inicialização e demais parâmetros da execução original.
- Uma repetição e limite de 1.800 segundos.
- Resultados, logs, checkpoints e rotas em uma nova pasta, por exemplo results/lb_two_edges_pilot/.
- Configuração identificando explicitamente o LB utilizado.
- Nenhuma alteração ou sobrescrita dos resultados anteriores.

Garanta que a retomada não pule esse teste por confundi-lo com a execução anterior.

Execute apenas as validações curtas. Não inicie o teste de 30 minutos: deixe o comando pronto para eu executar.

Indique quais métricas comparar com o resultado anterior para decidir se vale adotar o novo LB: conclusão dentro do prazo, tempo total, nós expandidos, tempo gasto no LB e melhor custo encontrado. Se ambos derem timeout, não declare um vencedor apenas pela quantidade de nós processados.
````

### Desdobramentos consolidados

O limite das duas arestas foi inicialmente implementado e validado em paralelo ao método anterior. Após essa comparação, foi solicitado que o solver utilizasse somente a formulação dos slides e que a documentação registrasse a mudança e seu possível custo por nó. A abstração configurável entre dois limitantes foi então removida do fluxo corrente, enquanto o limite por AGM residual permaneceu documentado como etapa inicial da evolução.

Os testes verificaram a admissibilidade em rotas parciais pequenas e a igualdade com o custo exato em rotas completas. O piloto e os resultados anteriores foram mantidos separados, sem sobrescrita. O efeito principal registrado não foi uma garantia de menor tempo por nó: o novo cálculo poderia custar mais, embora produzisse uma estimativa diferente para orientar a busca.

## 5. Cinco estratégias de inicialização e refatoração dos aproximativos — 20 de novembro de 2026

Depois de estabilizar o solver e o limitante, foi solicitada a implementação das cinco estratégias exigidas no TP2 conforme os algoritmos apresentados em aula. As revisões seguintes concentraram-se na estrutura compartilhada dos aproximativos e na cobertura de testes das funções centrais.

### Prompt principal

````text
Refatore o arquivo `approximation.py` para compartilhar a construção do circuito euleriano e sua conversão em ciclo hamiltoniano entre as estratégias **Twice Around the Tree** e **Christofides**.

### 1. Funções compartilhadas

Mantenha as funções existentes:

- `_minimum_spanning_tree_edges()`: Prim denso, com desempates determinísticos.
- `_minimum_weight_perfect_matching()`: Blossom via NetworkX.
- `_eulerian_circuit()`: Hierholzer, preservando o suporte a arestas paralelas por identificadores próprios.

Crie a função:
```python
def _eulerian_to_hamiltonian(
    circuit: tuple[int, ...], dimension: int
) -> tuple[int, ...]:
```

Ela deve:

- Receber um circuito euleriano.
- Aplicar *shortcutting*, mantendo somente a primeira ocorrência de cada vértice.
- Retornar uma permutação dos vértices, sem repetir a origem no final, seguindo a convenção atual do projeto.
- Validar que todos os vértices foram visitados exatamente uma vez.
- Tratar corretamente instâncias pequenas.

### 2. Refatorar Twice Around the Tree

Substitua a abordagem atual baseada em `_tree_preorder()` pela construção explícita:

1. Calcular a AGM com `_minimum_spanning_tree_edges()`.
2. Duplicar todas as arestas da AGM, formando um multigrafo euleriano.
3. Chamar `_eulerian_circuit()`.
4. Chamar `_eulerian_to_hamiltonian()`.
5. Retornar a rota resultante.

Remova `_tree_preorder()` caso não seja mais utilizada.

### 3. Refatorar Christofides

Preserve as etapas existentes:

1. Calcular a AGM.
2. Identificar os vértices de grau ímpar.
3. Calcular o matching perfeito mínimo.
4. Formar o multigrafo com AGM + matching.
5. Construir o circuito euleriano.

Substitua o código de *shortcutting* atualmente implementado dentro de `christofides_route()` por uma chamada à nova função compartilhada.

Adicione uma validação explícita de que o matching cobre todos os vértices de grau ímpar exatamente uma vez.

### 4. Requisitos

- Preserve as assinaturas públicas `twice_around_tree_route()` e `christofides_route()`.
- Preserve a representação atual das rotas e a compatibilidade com o restante do projeto.
- Mantenha o comportamento determinístico, inclusive nos empates.
- Preserve o tratamento de instâncias com 0, 1 ou 2 vértices.
- Atualize as docstrings para refletir a nova implementação.
- Não introduza dependências adicionais.
- Mantenha as garantias teóricas documentadas: 2 para Twice Around the Tree e 1,5 para Christofides, sob custos métricos.
- Evite refatorações fora do escopo.

### 5. Testes

Execute os testes existentes e adicione ou ajuste testes unitários para verificar:

- Funcionamento do circuito euleriano com arestas paralelas.
- Conversão correta de Euleriano para Hamiltoniano.
- Validade das rotas retornadas pelos dois algoritmos.
- Casos com 0, 1 e 2 vértices.
- Reprodutibilidade dos resultados.
- Matching perfeito cobrindo todos os vértices ímpares.

**Importante:** como a pré-ordem da AGM e o percurso euleriano explícito podem produzir rotas diferentes dependendo da ordem de visita, não exija que a nova implementação retorne exatamente a mesma sequência anterior. O importante é preservar a correção, o determinismo e a garantia de aproximação.

Ao finalizar, apresente um resumo das alterações, dos testes executados e dos respectivos resultados.
````

### Desdobramentos consolidados

A implementação foi progressivamente ampliada com as estratégias trivial, Vizinho Mais Próximo, fecho convexo com inserção gulosa, Twice-around-the-tree e Christofides sob uma interface comum. Durante a revisão, foi solicitada a redução de testes triviais e maior cobertura das cinco estratégias e das funções algorítmicas centrais. Foram mantidos desempates determinísticos, validação de permutações e tratamento de instâncias pequenas, colinearidade e coordenadas repetidas. Prim denso foi usado para AGM, Blossom via NetworkX para matching perfeito mínimo e Hierholzer para os circuitos eulerianos.

A refatoração substituiu a pré-ordem direta da AGM no Twice-around-the-tree pela duplicação explícita das arestas, seguida por Hierholzer e pelo atalho compartilhado `_eulerian_to_hamiltonian`. Christofides passou a reutilizar a mesma conversão e a validar a cobertura dos vértices ímpares pelo matching. A suíte foi reduzida em casos triviais e redirecionada para funções centrais e cobertura das cinco estratégias.

O resultado verificável está em [approximation.py](../../src/traveling_salesman_optimization/approximation.py), [initial_solutions.py](../../src/traveling_salesman_optimization/initial_solutions.py) e [test_warm_start_strategies.py](../../tests/unit/test_warm_start_strategies.py). As garantias teóricas de fatores 2 e 1,5 permaneceram documentadas como condicionais a custos métricos; a análise posterior constatou violações da desigualdade triangular após o arredondamento em parte das instâncias locais.

## 6. Auditoria de conformidade e instrumentação científica — 20 de novembro de 2026

Com a implementação funcional, o aluno solicitou uma revisão assistida por IA para confrontar o código existente com o enunciado e o material das aulas. O escopo foi delimitado pelo aluno: identificar e corrigir somente inconformidades, evitar alterações desnecessárias e registrar as correções acompanhadas de suas justificativas. A IA auxiliou na identificação das lacunas e na execução dos ajustes, dentro dessas restrições, como etapa complementar às decisões algorítmicas e refatorações descritas neste histórico.

### Desdobramentos consolidados

A auditoria não registrou erro matemático crítico no Branch-and-Bound best-first, no limite das duas arestas, nas cinco inicializações, em Prim, Blossom, Hierholzer ou no atalho euleriano. As correções solicitadas concentraram-se em lacunas de instrumentação e protocolo: profiling individual de AGM, matching, circuito e atalho; contador de nós gerados; impressão digital da implementação e das dependências; execução conjunta com `--all-strategies`; encerramento da árvore de processos; consistência entre checkpoint e TOUR; características geométricas; tratamento de censura; e modelos com R² e RMSE.

O schema experimental foi elevado para 4. Os picos por fase foram documentados como *high-water marks* do processo worker, não como memória exclusiva nem aditiva das subrotinas. Gaps passaram a depender de ótimo certificado para o mesmo SHA-256, e timeouts foram tratados como observações censuradas.

As validações registradas nessa fase foram Ruff sem falhas, `25 passed`, `git diff --check` limpo e um *smoke test* das cinco estratégias em `example_crossing`, todas com custo 40. O analisador processou 16 linhas históricas, identificou violações triangulares em 14 instâncias e ajustou o modelo temporal somente sobre dez execuções certificadas. Esses testes curtos, armazenados em `.tmp/`, não foram incorporados como base científica do TP.

## 7. Refatorações da versão final e novo painel experimental — 23 e 24 de novembro de 2026

Os resultados da etapa intermediária continham 75 células pareadas: 25 provas de otimalidade e 50 timeouts. A revisão seguinte concentrou-se na repetição de estados, no tamanho da heap e no custo de copiar rotas parciais.

### Prompt principal

````text
1. **Aplicar dominância de estados:** para `(vértice_atual, não_visitados)`, manter apenas o menor custo parcial. Hoje caminhos equivalentes são processados repetidamente.
2. **Podar antes do `heappush`:** em [branch_and_bound.py (line 394)](</C:/Users/Chrystian/Documents/GitHub Projects/TravelingSalesmanOptimization/src/traveling_salesman_optimization/branch_and_bound.py:394>), filhos com `child_bound >= best_cost` ainda são copiados e inseridos no heap.
3. **Não armazenar a rota inteira em cada estado:** `partial_route + (...)` cria milhões de tuplas. Usar ponteiro para o estado pai reduziria muito o pico atual de aproximadamente 10,8 GiB.

Faça esses 3 primeiros e salve em patches.

Ao finalizar me de o comando q devo rodar para refazer os expeerimetos necessarios
````

### Desdobramentos consolidados

A refatoração implementou dominância por `(vértice_atual, não_visitados)`, rejeição de estados dominados antes do cálculo do limite, descarte de entradas obsoletas ao sair da heap, poda antes de `heappush` e nós de rota com referência ao pai. A rota completa passou a ser materializada somente quando uma folha melhorava a incumbente. O limite das duas arestas, a política best-first e as cinco estratégias foram preservados.

Como a semântica dos contadores mudou, `instrumentation_version` passou a 5, enquanto o schema permaneceu 4. `generated_nodes` passou a contar cada filho considerado; `pruned_nodes` passou a agregar limite, dominância e encerramento coletivo da fronteira; e `lower_bound_calls` pôde ficar abaixo de `generated_nodes` porque a dominância ocorre antes do limitante. A validação registrou 26 testes aprovados, Ruff e formatação sem falhas e `git diff --check` limpo. Um ensaio curto com `sub_pr107_20_seed301` e fecho convexo, anteriormente interrompido aos 1.800 segundos, comprovou o ótimo em aproximadamente 16,2 segundos; esse ensaio foi tratado somente como evidência inicial.

O prompt também solicitava salvar as mudanças em patches. Não há arquivo de patch registrado entre os artefatos finais, portanto esse item não é apresentado como concluído.

As mudanças invalidaram o reaproveitamento direto das métricas intermediárias. Foi preparado um novo lote, em diretório separado, com 15 instâncias, cinco estratégias, uma repetição, 75 execuções, timeout de 1.800 segundos, checkpoints de 30 segundos e margem externa de dez segundos. A coleta efetiva ocorreu entre 23 de novembro, às 11h58, e 24 de novembro de 2026, às 1h35, no horário de Brasília.

| Estratégia | Execuções | Ótimos comprovados | Timeouts |
|---|---:|---:|---:|
| Christofides | 15 | 10 | 5 |
| Fecho convexo | 15 | 11 | 4 |
| Vizinho Mais Próximo | 15 | 11 | 4 |
| Trivial | 15 | 11 | 4 |
| Twice-around-the-tree | 15 | 11 | 4 |
| **Total** | **75** | **54** | **21** |

O painel final converteu 29 células antes interrompidas em provas dentro do mesmo prazo. A comparação não isola o efeito individual de cada refatoração, e os contadores não devem ser agregados em uma única regressão porque sua semântica mudou. Os artefatos permanecem separados em `experiments/results/intermediate/` e `experiments/results/final/`; os baselines e o piloto anteriores estão em `experiments/results/initial/`.

## 8. Análise independente dos aproximativos — 23 de novembro de 2026

Antes da consolidação final do artigo, foi solicitada uma análise de Christofides e Twice-around-the-tree como solvers independentes, separada de seu papel como warm-start do Branch-and-Bound.

### Prompt principal

````text
Atualize o relatório LaTeX do [main.tex](docs/report/main.tex) , acrescentando uma subseção **“Avaliação Independente dos Algoritmos Aproximativos”** em Experimentos e Resultados.

Utilize exclusivamente os dados já coletados para comparar **Christofides e Twice-around-the-tree como solvers independentes**, e não apenas como warm-start do Branch-and-Bound. [current](experiments/results/current/)

Apresente tempo de execução, memória, custo das rotas, gap em relação ao ótimo e profiling das subrotinas. Inclua tabelas e análises críticas, seguindo o padrão científico SBC.

**Não execute novos experimentos**, não invente dados e não altere os resultados existentes. Reaproveite os CSVs disponíveis, mantenha a análise das cinco estratégias de inicialização separada e atualize as conclusões para contemplar essa comparação.

Nao mexa no [optimized-v5](experiments/results/optimized-v5/) nem no codigo pq to rodando uma nova versao futura do codigo
````

### Desdobramentos consolidados

A análise utilizou `initialization_seconds`, `initial_route_cost`, os ótimos certificados e as métricas de AGM, matching, circuito e atalho, sem executar novos experimentos. O tempo da busca exata foi excluído. A memória foi tratada como pico residente observado durante as fases, sem atribuí-la como alocação exclusiva do aproximativo.

O relatório registrou que Christofides retornou a rota de menor custo nas 15 comparações pareadas, enquanto Twice-around-the-tree foi mais rápido nas 15. Nas 14 instâncias com ótimo conhecido, os gaps médios foram 9,25% e 26,45%, respectivamente. O matching perfeito concentrou a maior parcela do tempo de Christofides. Essas conclusões foram mantidas separadas da comparação dos cinco warm-starts.

Após a elaboração inicial da subseção, o aluno conduziu revisões sucessivas da apresentação dos resultados, orientando a forma de construção e exibição dos gráficos e solicitando mudanças no estilo e na organização das tabelas. A IA foi utilizada para implementar esses ajustes no relatório e adequar a apresentação ao padrão científico adotado. Esse processo de refinamento prosseguiu na revisão científica final, descrita na etapa 9, com critérios explícitos de comparabilidade, rastreabilidade e interpretação das métricas.

Os nomes `current` e `optimized-v5` aparecem acima porque pertencem ao prompt original. Na organização final do repositório, essas etapas foram renomeadas para `intermediate` e `final`, sem alteração dos dados experimentais.

## 9. Consolidação dos resultados e revisão científica final — 24 de novembro de 2026

Depois da coleta do novo painel, foi solicitada a atualização da análise e da documentação a partir dos resultados efetivamente obtidos, com inspeção das alterações pelo `git diff`. A revisão científica final foi então delimitada pelo prompt abaixo, sem autorização para novos experimentos de Branch-and-Bound.

### Prompt principal

````text
Revise o `main.tex` do TP2 considerando o relatório atual da implementação **v5** e o enunciado do trabalho.

O relatório já apresenta uma análise completa das cinco estratégias de warm-start, dos dois aproximativos independentes, dos 54 resultados ótimos, dos 21 timeouts, da refatoração, do profiling e da sensibilidade. **Não refaça essas análises nem reestruture desnecessariamente o artigo.**

Concentre as melhorias nos seguintes pontos:

1. **Visualização das regressões (Seção 4.3):** gere gráficos científicos de tempo e memória em função de N, mostrando observações reais e curvas ajustadas, com R² e RMSE. Use os dados já existentes e identifique corretamente as observações censuradas, sem incluí-las indevidamente no ajuste.
2. **Comparação antes × v5:** acrescente uma tabela sintética com provas de otimalidade (25 → 54), timeouts (50 → 21), chamadas do lower bound, expansões, tempo acumulado de busca e pico de memória. Evidencie os 29 timeouts convertidos em provas. Verifique a comparabilidade das métricas e não confunda redução do tempo acumulado do lote com speedup individual.
3. **Ambiente experimental (Seção 4.1):** complemente a especificação de hardware com modelo da CPU e RAM instalada, caso essas informações estejam disponíveis nos registros do projeto. Discuta brevemente a influência do ambiente computacional nos timeouts.
4. **Base experimental:** explique melhor como foram geradas as 12 subinstâncias da TSPLIB, incluindo instâncias de origem, procedimento de seleção e sementes, conforme o código existente. Justifique metodologicamente a escolha sem afirmar que o enunciado autoriza explicitamente subamostragem.
5. **Revisão científica e editorial:** confira a interpretação dos contadores de poda, especialmente dominância, limite inferior e fronteira remanescente. Corrija o erro de renderização de `lower_bound_calls` na Seção 2.6 e procure eventuais problemas semelhantes.

**Restrições:**

- Não execute novos experimentos de Branch-and-Bound.
- Utilize os CSVs da v5 e da versão anterior, preservando sua rastreabilidade.
- Não invente dados nem atribua ganhos a alterações individuais sem evidência.
- Preserve todas as análises corretas já existentes, especialmente a avaliação independente dos aproximativos.
- Evite redundância e aumento desnecessário do número de páginas.
- Atualize o texto apenas onde os novos elementos realmente exigirem.
- Compile o LaTeX e verifique os gráficos, as tabelas e a formatação final no padrão SBC.

O objetivo é **finalizar e fortalecer o artigo existente**, não reconstruí-lo.
````

### Desdobramentos consolidados

A revisão confrontou os CSVs das etapas intermediária e final e restringiu a comparação às 75 células correspondentes. Os 29 casos convertidos foram identificados como as mesmas combinações de instância e estratégia. A redução do tempo acumulado do lote foi descrita como medida agregada, sem ser apresentada como *speedup* individual. Métricas cuja semântica mudou, especialmente poda, foram acompanhadas de ressalvas de comparabilidade.

Foram produzidos gráficos de tempo e memória em função de `n`, com observações censuradas identificadas e excluídas dos ajustes, e foram exibidos R² e RMSE. A base experimental passou a explicar a origem, seleção e sementes das 12 subinstâncias. Os registros disponíveis não sustentavam o nome comercial da CPU nem a RAM instalada; essas informações não foram inventadas. A interpretação de `lower_bound_calls`, dominância e fronteira remanescente foi revisada, e o erro de renderização citado no prompt foi corrigido.

Interações de refinamento reorganizaram as tabelas por estratégia, acrescentaram o número de vértices, substituíram por `NA` os campos sem interpretação certificada em timeouts e incluíram uma discussão sobre censura, pressão de memória e limitações da implementação. Os diagramas também foram regenerados após as refatorações: há um fluxo geral do experimento, um grafo do Branch-and-Bound e grafos separados para as cinco estratégias. Ajustes visuais sucessivos foram consolidados sem reproduzir cada tentativa.

O resultado documental é o artigo SBC em [main.tex](../report/main.tex), acompanhado de gráficos, tabelas, diagramas e PDF compilado. Ele apresenta as cinco inicializações, os dois aproximativos independentes, profiling, análise de sensibilidade, comparação entre as etapas intermediária e final, 54 provas, 21 timeouts e as limitações da evidência. As três fases experimentais são identificadas no repositório como **inicial**, **intermediária** e **final**. A expressão `v5`, presente no prompt principal acima, corresponde à nomenclatura histórica da implementação final; `instrumentation_version=5` permanece somente como identificador técnico necessário à reprodução.

## Síntese cronológica dos resultados preservados

| Etapa | Decisão ou atividade central | Resultado efetivamente registrado |
|---|---|---|
| Inicial | Estrutura Python, CI, relatório SBC e solver exato de referência | Infraestrutura validável; parser TSPLIB; Branch-and-Bound posteriormente corrigido para best-first; baseline e piloto preservados em `experiments/results/initial/` |
| Intermediária | Executor reproduzível, limite das duas arestas, cinco estratégias, profiling e auditoria | Painel pareado com 75 células, 25 provas de otimalidade e 50 timeouts; gargalos de limite, fronteira e memória documentados em `experiments/results/intermediate/` |
| Final | Dominância de estados, poda antes da heap e prefixos de rota compartilhados | Novo painel com 75 execuções, 54 provas e 21 timeouts; 29 conclusões adicionais dentro do prazo; dados preservados em `experiments/results/final/` |

Solicitações de execução longa só foram tratadas como resultados quando os CSVs e artefatos correspondentes estavam presentes. Decisões abandonadas — DFS, limite baseado em AGM e pré-ordem direta no Twice-around-the-tree — permanecem neste histórico porque explicam a evolução técnica, mas não descrevem a implementação final.
