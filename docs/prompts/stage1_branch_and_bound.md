# Resumo do prompt — etapa 1 do TP2

Implementar a primeira etapa do Trabalho Prático 2 de Algoritmos 2 da UFMG,
após ler o enunciado e inspecionar o repositório. O objetivo era entregar um
solver exato para o Problema do Caixeiro Viajante (TSP) geométrico, limitado ao
escopo de leitura, custos, Branch-and-Bound, rota inicial trivial e validação.

Requisitos solicitados:

- ler instâncias TSPLIB `EUC_2D`, preservando IDs e ordem dos vértices;
- centralizar custos em uma matriz de distâncias, usando o arredondamento
  TSPLIB `int(distância + 0.5)` e uma função comum para custo de rota fechada;
- implementar Branch-and-Bound exato com busca best-first e fila de prioridade
  ordenada pelo limite inferior, mantendo o primeiro vértice como origem e a
  rota na ordem do arquivo como limite superior inicial;
- usar, para uma rota parcial, o limite inferior composto por custo percorrido,
  AGM dos vértices não visitados, menor conexão do vértice atual para esse
  conjunto e menor conexão desse conjunto para a origem;
- retornar rota, custo ótimo, nós expandidos e podados, documentando
  precisamente a semântica dos contadores;
- manter a estratégia de rota inicial separada do solver para permitir as
  heurísticas das etapas seguintes;
- disponibilizar CLI para arquivos `.tsp` e validar o resultado contra força
  bruta em instâncias pequenas, incluindo uma em que a rota trivial não fosse
  ótima;
- deixar heurísticas, experimentos e relatório para as próximas etapas.

## Revisão da estratégia: de DFS para best-first

Durante a revisão, foi observado que a primeira versão usava busca em
profundidade (DFS), seguindo um ramo por vez. Foi então solicitada explicitamente
a correção para best-first com fila de prioridade, de modo que o estado com
menor limite inferior fosse escolhido entre todos os estados ativos, conforme
a estratégia apresentada na Aula 12: os filhos têm prioridades diferentes e o
de menor estimativa é tratado como o mais promissor. A implementação e os
testes de instrumentação foram atualizados para refletir essa mudança de ordem
da busca.

## Complemento: automação experimental

Foi solicitado automatizar os experimentos do Branch-and-Bound com a
inicialização trivial: processos isolados, limite de 1.800 segundos, CSV por
execução, perfil de tempo/memória e de subrotinas, checkpoints, timeout com
incumbente parcial, rotas salvas, retomada sem duplicatas e validação curta.
