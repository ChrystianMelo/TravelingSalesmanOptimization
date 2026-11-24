# Evolução da documentação, dos diagramas e da integração contínua

## Papel da documentação no desenvolvimento

Desde a configuração inicial, tratei a documentação como parte da
implementação e não como uma etapa posterior de apresentação. O TP2 exige
auditoria das estruturas de dados, profiling, argumentação sobre gargalos,
resultados reproduzíveis e histórico do uso de IA. Por isso, uma alteração no
código somente poderia ser considerada completa quando seus contratos,
contadores, limitações e efeitos experimentais estivessem refletidos nos
artefatos correspondentes.

Adotei como fontes de verdade, em ordem de responsabilidade:

- `docs/assignment/tp2.pdf` para os requisitos do trabalho;
- o código em `src/` para o comportamento efetivamente implementado;
- os testes para invariantes e regressões verificáveis;
- os CSVs, JSONs e configurações em `experiments/results/` para resultados
  executados;
- os documentos técnicos e o relatório para explicar e interpretar essas
  evidências;
- `docs/prompts/` para registrar decisões, revisões e intervenções assistidas
  por IA.

Essa separação evitou documentar funcionalidades planejadas como se já
estivessem prontas e impediu que números experimentais fossem incluídos antes
de sua coleta.

## Estrutura documental definida no início

Na primeira etapa, organizei o repositório para que cada tipo de informação
tivesse um destino explícito:

- `README.md`: apresentação, instalação, execução, estado atual e navegação;
- `docs/assignment/`: enunciado original usado como fonte primária;
- `docs/implementation/`: decisões e detalhes dos algoritmos;
- `docs/analysis/`: baselines e análises intermediárias;
- `docs/architecture.md`: módulos, contratos, chamadas e fluxos;
- `docs/diagrams/generated/`: fontes Mermaid e DOT geradas;
- `docs/report/`: artigo SBC, figuras e PDF compilado;
- `docs/prompts/`: histórico obrigatório do uso de IA;
- `experiments/README.md`: protocolo, schema, artefatos e semântica das
  métricas;
- `.github/workflows/`: integração contínua.

O relatório começou como um esqueleto em LaTeX, sem resultados inventados. O
README começou descrevendo a estrutura e os objetivos, sem prometer
algoritmos ainda inexistentes. Ambos foram ampliados somente à medida que o
projeto ganhou implementação e evidências.

## README como porta de entrada viva

O README foi atualizado durante o desenvolvimento para acompanhar o estado
real do projeto. Ele passou a reunir:

- os três algoritmos exigidos e as cinco estratégias de warm-start;
- links para o enunciado, arquitetura e documentação das estratégias;
- requisitos e configuração do ambiente Python 3.12;
- comandos da CLI, executor de experimentos e analisador;
- definições de nós gerados, expandidos e podados;
- estrutura atual dos diretórios;
- comandos locais equivalentes aos executados pela CI;
- requisitos do relatório e da entrega.

Mudanças semânticas foram refletidas no README. Quando a instrumentação v5
passou a descartar estados por dominância antes do limite inferior, por
exemplo, deixou de ser válida a relação anterior entre nós gerados e chamadas
do limitante. A documentação passou a declarar que
`lower_bound_calls <= generated_nodes` e que a poda inclui dominância, limite
inferior e encerramento coletivo da fronteira.

## Documentação técnica e experimental

O documento `docs/implementation/warm-start-strategies.md` foi criado para
explicar separadamente as cinco estratégias, suas representações,
complexidades, critérios de desempate e subrotinas compartilhadas. Essa
separação evita sobrecarregar o README com detalhes algorítmicos e permite
confrontar a descrição com as funções correspondentes.

Em `docs/analysis/`, foram preservadas análises intermediárias, como o baseline
trivial e a revisão do limite inferior das duas arestas. Esses registros
distinguem decisões tomadas antes da bateria final dos resultados que
efetivamente entraram no artigo.

O arquivo `experiments/README.md` evoluiu junto com o executor. Ele documenta:

- processo isolado por execução;
- prazo cooperativo e salvaguarda externa;
- checkpoints e escrita atômica;
- retomada e reexecução explícita;
- arquivos CSV, JSON, TOUR e logs;
- medição de tempo e pico de memória;
- diferença entre incumbente e ótimo certificado;
- schema e semântica dos contadores;
- impressão digital da implementação e das dependências.

Quando a implementação mudou de forma incompatível com os contadores, a
versão da instrumentação foi elevada e um novo diretório experimental foi
usado. Assim, o painel `optimized-v5` não foi misturado silenciosamente com o
painel anterior.

## Arquitetura e diagramas

A documentação de arquitetura começou como uma descrição modular e foi
ampliada para combinar duas classes de visualização:

1. diagramas extraídos do código, que reduzem o risco de divergência;
2. fluxos conceituais curados, usados quando a intenção algorítmica não pode
   ser inferida apenas por chamadas estáticas.

O estado atual de `docs/architecture.md` inclui:

- fluxo geral dos experimentos;
- dependências entre módulos;
- classes e contratos principais;
- caminho da CLI até o solver;
- grafo de chamadas do Branch-and-Bound;
- um grafo de chamadas separado para cada estratégia;
- fluxo curado do Branch-and-Bound;
- fluxo comparativo das cinco inicializações.

O script `scripts/generate_diagrams.py` automatiza essa documentação. Ele usa:

- Code2flow para grafos de chamadas;
- Pyreverse para UML de módulos e classes;
- Graphviz para renderizar figuras PDF;
- Mermaid e DOT como fontes versionáveis.

Os blocos automáticos de `docs/architecture.md` ficam entre marcadores
`BEGIN GENERATED` e `END GENERATED`. O gerador substitui somente esses blocos,
preservando as explicações e fluxos manuais externos aos marcadores. Os PDFs
necessários ao artigo são escritos em `docs/report/figures/`.

Chamadas feitas dinamicamente por meio de `INITIAL_ROUTE_STRATEGIES` não são
detectadas de forma confiável pelo Code2flow. Por isso, o gerador mantém uma
lista explícita das funções pertencentes a cada estratégia. Essa decisão e sua
limitação estão documentadas, em vez de apresentar o grafo automático como
uma representação completa sem ressalvas.

Para regenerar os diagramas, foram definidos os comandos:

```bash
python -m pip install -e ".[docs]"
python scripts/generate_diagrams.py
```

O Graphviz precisa estar disponível no `PATH` ou ser informado por `--dot`.
Os arquivos gerados não devem ser corrigidos manualmente; alterações devem ser
feitas no código, no gerador ou nos trechos conceituais apropriados.

## Atualizações motivadas por revisões do algoritmo

A documentação acompanhou as principais revisões discutidas durante o
desenvolvimento:

### Troca de DFS por best-first

A primeira versão do Branch-and-Bound usava recursão em profundidade. Após a
auditoria, a fronteira foi substituída por uma heap global best-first. Essa
mudança atualizou a explicação arquitetural, o fluxo do solver, os testes de
contadores e a discussão no relatório. O histórico registra que ambas as
políticas poderiam preservar a exatidão, mas somente a segunda correspondia à
decisão adotada no projeto.

### Substituição do limite baseado em AGM

O limite inferior inicial baseado em AGM residual foi substituído pelo limite
das duas arestas incidentes. Foram atualizados o documento de análise, a
configuração experimental, os testes de admissibilidade e a explicação no
relatório. A documentação também registrou os casos degenerados e as arestas
fixadas ou proibidas em cada estado parcial.

### Instrumentação e automação experimental

Quando foram adicionados profiling por subrotina, nós gerados, impressão
digital dos fontes, execução conjunta das cinco estratégias e análise de
sensibilidade, README, documentação experimental, arquitetura e artigo foram
atualizados em conjunto. A descrição dos tempos passou a explicitar quais
medidas estão contidas em outras, evitando somas incorretas.

### Dominância, poda antecipada e prefixos compartilhados

A otimização posterior adicionou dominância por estado, poda antes de
`heappush` e representação da rota por referência ao pai. O fluxo do
Branch-and-Bound, a UML, os grafos de chamadas, os contadores e a seção de uso
de IA do relatório passaram a representar essa versão. Um novo painel com 75
execuções foi coletado porque os resultados da implementação anterior não
eram diretamente reutilizáveis.

### Resultados, tabelas e análise crítica

As tabelas do relatório foram reorganizadas por estratégia para preservar o
status individual de cada execução. Foi incluído o número de vértices de cada
instância, e campos sem interpretação certificada em timeout foram mostrados
como `NA`.

Depois da primeira bateria, foi acrescentada uma discussão crítica sobre
censura, viés da amostra concluída, limitações dos contadores parciais, custo
do limite inferior, crescimento da heap, encerramento externo e melhorias
possíveis. Após a instrumentação v5 e o novo painel, tabelas, modelos e
conclusões foram atualizados com os novos resultados, mantendo separadas as
duas versões experimentais.

## Relatório científico

O relatório em `docs/report/main.tex` foi desenvolvido no formato SBC e passou
a integrar:

- introdução e objetivos;
- arquitetura e documentação automática;
- estruturas de dados e algoritmos;
- profiling e auditoria;
- uso de IA com exemplos concretos de revisão;
- protocolo experimental reproduzível;
- tabelas por estratégia;
- análise de timeouts e ameaças à validade;
- modelos de complexidade e sensibilidade;
- avaliação independente das aproximações;
- conclusões e limitações.

As figuras do artigo são produzidas pelo mesmo gerador usado pela documentação
de arquitetura, evitando manter manualmente duas representações da mesma
estrutura. O PDF é recompilado após mudanças relevantes no LaTeX ou nas
figuras e passa por inspeção visual, além da verificação de erros do compilador.

## Histórico de prompts e rastreabilidade da IA

O diretório `docs/prompts/` foi mantido porque o enunciado exige a entrega do
histórico de uso de LLMs. Em vez de armazenar apenas solicitações isoladas, os
documentos consolidam:

- o objetivo e os limites definidos pelo aluno;
- as decisões arquiteturais solicitadas;
- divergências identificadas durante a revisão;
- correções autorizadas;
- validações executadas;
- resultados que motivaram novas intervenções;
- restrições como não inventar experimentos e não criar commits
  automaticamente.

O histórico foi separado em documentos temáticos para que a configuração
inicial, a implementação das estratégias, a otimização do Branch-and-Bound e a
evolução da documentação possam ser auditadas sem depender do conteúdo
integral de uma conversa.
