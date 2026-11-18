# Resumo do prompt inicial

Preparar somente a infraestrutura inicial de um projeto Python para o Trabalho
Prático 2 de Algoritmos 2 da UFMG, sobre análise empírica e otimização de
algoritmos para o Problema do Caixeiro Viajante geométrico.

O projeto deveria usar o repositório DeliveryDispatch como referência de
organização, estilo e infraestrutura. O enunciado do TP2 deveria ser lido e
refletido fielmente no README, sem apresentar funcionalidades futuras como se
já estivessem implementadas.

Escopo solicitado:

- criar um README profissional, com objetivos, algoritmos exigidos,
  estratégias de warm-start, avaliação experimental, entregáveis, requisitos e
  instruções de instalação, execução e testes;
- organizar os diretórios `src/`, `tests/`, `data/`, `experiments/`, `docs/` e
  `scripts/`, incluindo espaços para instâncias, cenários, resultados,
  relatórios e histórico de prompts;
- configurar `pyproject.toml`, `.gitignore`, `.editorconfig`, pytest, Ruff e
  GitHub Actions para executar lint e testes em pushes e pull requests;
- adicionar apenas um ponto de entrada que imprimisse `Hello, World!` e um
  teste pytest trivial com `assert 1 == 1`;
- preparar um esqueleto de relatório em LaTeX no formato SBC, sem conteúdo ou
  resultados inventados.

Restrição central: nesta etapa não deveriam ser implementados algoritmos,
heurísticas, processamento de dados ou experimentos. Ao final, lint e testes
deveriam ser executados, sem criar commits automaticamente.

Posteriormente, foi solicitado que o README fosse integralmente em português e
que o enunciado `tp2.pdf` fosse mantido em `docs/assignment/`.
