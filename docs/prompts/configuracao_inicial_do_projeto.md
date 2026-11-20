# Definição da infraestrutura inicial do projeto

## Ponto de partida que defini

Comecei o trabalho delimitando a infraestrutura de um projeto Python para o
Trabalho Prático 2 de Algoritmos 2 da UFMG, dedicado à análise empírica e à
otimização de algoritmos para o Problema do Caixeiro Viajante geométrico. Nesta
fase, minha prioridade era estabelecer uma base verificável antes de permitir
qualquer implementação algorítmica.

Escolhi o repositório `DeliveryDispatch` apenas como referência de organização,
estilo e infraestrutura, sem transportar decisões de domínio automaticamente.
Também determinei que o enunciado do TP2 fosse tratado como fonte primária e
refletido fielmente na documentação, sem apresentar funcionalidades futuras
como se já estivessem implementadas.

## Estrutura e entregas que solicitei

- criar um README profissional em português, com objetivos, algoritmos
  exigidos, estratégias de warm-start, avaliação experimental, entregáveis,
  requisitos e instruções de instalação, execução e testes;
- organizar os diretórios `src/`, `tests/`, `data/`, `experiments/`, `docs/` e
  `scripts/`, incluindo espaços para instâncias, cenários, resultados,
  relatórios e histórico de prompts;
- configurar `pyproject.toml`, `.gitignore`, `.editorconfig`, pytest, Ruff e
  GitHub Actions para executar lint e testes em pushes e pull requests;
- adicionar somente um ponto de entrada que imprimisse `Hello, World!` e um
  teste pytest trivial com `assert 1 == 1`;
- preparar um esqueleto de relatório em LaTeX no formato SBC, sem conteúdo ou
  resultados inventados;
- manter o arquivo `tp2.pdf` em `docs/assignment/` como fonte primária dos
  requisitos do trabalho.

## Limites que mantive nesta etapa

Decidi não antecipar algoritmos, heurísticas, processamento de dados ou
experimentos nessa configuração inicial. O objetivo era primeiro validar a
arquitetura do repositório, a separação de responsabilidades e a automação
mínima. Ao final, solicitei a execução de lint e testes, sem criação automática
de commits.
