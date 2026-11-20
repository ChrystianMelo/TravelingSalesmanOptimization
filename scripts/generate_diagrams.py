"""Regenera os diagramas de arquitetura a partir do código-fonte do projeto."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src" / "traveling_salesman_optimization"
OUTPUT = ROOT / "docs" / "diagrams" / "generated"
ARCHITECTURE_DOC = ROOT / "docs" / "architecture.md"
REPORT_FIGURES = ROOT / "docs" / "report" / "figures"

CODE2FLOW_DIAGRAMS = {
    "calls-cli": (("main::main",), 4),
    "calls-branch-and-bound": (("solve_branch_and_bound",), 3),
}

STRATEGY_ENTRIES = (
    "trivial_initial_route",
    "nearest_neighbor_initial_route",
    "convex_hull_insertion_initial_route",
    "twice_around_tree_route",
    "christofides_route",
)

STRATEGY_FUNCTIONS = (
    *STRATEGY_ENTRIES,
    "_convex_hull_vertices",
    "_cross_product",
    "_minimum_spanning_tree_edges",
    "_minimum_weight_perfect_matching",
    "_eulerian_circuit",
    "_eulerian_to_hamiltonian",
)

EMBEDDED_DIAGRAMS = (
    "calls-cli",
    "calls-branch-and-bound",
    "calls-initial-strategies",
    "uml-classes",
    "uml-modules",
)

REPORT_CALL_DIAGRAMS = {
    "calls-branch-and-bound",
    "calls-initial-strategies",
}


def _tool_path(name: str) -> str:
    """Localiza um console script no ambiente ativo ou ao lado do Python."""

    executable_name = f"{name}.exe" if sys.platform == "win32" else name
    system_candidates = (
        (r"C:\Program Files\Graphviz\bin\dot.exe",)
        if sys.platform == "win32" and name == "dot"
        else ()
    )
    candidates = (
        shutil.which(name),
        str(Path(sys.executable).resolve().parent / executable_name),
        *system_candidates,
    )
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return candidate
    raise RuntimeError(
        f"{name} não foi encontrado. Instale as dependências com "
        'python -m pip install -e ".[docs]".'
    )


def _run(command: Sequence[str]) -> None:
    subprocess.run(command, cwd=ROOT, check=True)


def _read_code2flow_graph(path: Path) -> tuple[set[str], set[tuple[str, str]]]:
    document: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    graph = document["graph"]
    names_by_uid = {uid: str(node["name"]) for uid, node in graph["nodes"].items()}
    nodes = set(names_by_uid.values())
    edges = {
        (names_by_uid[edge["source"]], names_by_uid[edge["target"]]) for edge in graph["edges"]
    }
    return nodes, edges


def _call_graph_mermaid(
    nodes: Iterable[str], edges: Iterable[tuple[str, str]], entries: Iterable[str]
) -> str:
    """Converte a saída JSON do Code2flow em Mermaid compacto e estável."""

    sorted_nodes = sorted(set(nodes))
    identifiers = {name: f"n{position}" for position, name in enumerate(sorted_nodes)}
    modules: dict[str, list[str]] = {}
    for name in sorted_nodes:
        module, _, function = name.partition("::")
        modules.setdefault(module, []).append(function or module)

    lines = [
        "%% Gerado por scripts/generate_diagrams.py a partir da saída do Code2flow.",
        "flowchart LR",
    ]
    for module, functions in sorted(modules.items()):
        module_id = re.sub(r"[^a-zA-Z0-9_]", "_", module)
        lines.append(f'  subgraph module_{module_id}["{module}.py"]')
        lines.append("    direction TB")
        for function in functions:
            qualified_name = f"{module}::{function}"
            lines.append(f'    {identifiers[qualified_name]}["{function}()"]')
        lines.append("  end")

    for source, target in sorted(set(edges)):
        lines.append(f"  {identifiers[source]} --> {identifiers[target]}")

    entry_names = {
        name
        for name in sorted_nodes
        if any(name == entry or name.endswith(f"::{entry}") for entry in entries)
    }
    if entry_names:
        lines.append("  classDef entry fill:#dbeafe,stroke:#2563eb,stroke-width:2px")
        lines.append(
            "  class " + ",".join(identifiers[name] for name in sorted(entry_names)) + " entry"
        )
    return "\n".join(lines) + "\n"


def _call_graph_dot(
    nodes: Iterable[str], edges: Iterable[tuple[str, str]], entries: Iterable[str]
) -> str:
    """Converte o grafo do Code2flow em DOT para as figuras do relatório."""

    sorted_nodes = sorted(set(nodes))
    identifiers = {name: f"n{position}" for position, name in enumerate(sorted_nodes)}
    entry_names = {
        name
        for name in sorted_nodes
        if any(name == entry or name.endswith(f"::{entry}") for entry in entries)
    }
    modules: dict[str, list[str]] = {}
    for name in sorted_nodes:
        module, _, function = name.partition("::")
        modules.setdefault(module, []).append(function or module)

    lines = [
        "// Gerado por scripts/generate_diagrams.py a partir da saída do Code2flow.",
        "digraph calls {",
        '  graph [rankdir=LR, bgcolor="transparent", pad=0.15, nodesep=0.25, ranksep=0.5];',
        '  node [shape=box, style="rounded,filled", fillcolor="#f8fafc",',
        '        color="#64748b", fontname="Helvetica", fontsize=9, margin="0.10,0.06"];',
        '  edge [color="#64748b", arrowsize=0.7];',
    ]
    for module, functions in sorted(modules.items()):
        module_id = re.sub(r"[^a-zA-Z0-9_]", "_", module)
        lines.extend(
            (
                f"  subgraph cluster_{module_id} {{",
                f'    label="{module}.py";',
                '    color="#cbd5e1";',
                '    fontname="Helvetica";',
                "    fontsize=10;",
            )
        )
        for function in functions:
            qualified_name = f"{module}::{function}"
            attributes = (
                ', fillcolor="#dbeafe", color="#2563eb", penwidth=2'
                if qualified_name in entry_names
                else ""
            )
            lines.append(f'    {identifiers[qualified_name]} [label="{function}()"{attributes}];')
        lines.append("  }")

    for source, target in sorted(set(edges)):
        lines.append(f"  {identifiers[source]} -> {identifiers[target]};")
    lines.append("}")
    return "\n".join(lines) + "\n"


def _render_dot(dot_tool: str, source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    _run((dot_tool, "-Tpdf", str(source), "-o", str(destination)))


def _write_call_graph(
    diagram_name: str,
    nodes: Iterable[str],
    edges: Iterable[tuple[str, str]],
    entries: Iterable[str],
    dot_tool: str,
) -> None:
    mermaid = _call_graph_mermaid(nodes, edges, entries)
    (OUTPUT / f"{diagram_name}.mmd").write_text(mermaid, encoding="utf-8", newline="\n")
    dot_source = OUTPUT / f"{diagram_name}.dot"
    dot_source.write_text(
        _call_graph_dot(nodes, edges, entries),
        encoding="utf-8",
        newline="\n",
    )
    if diagram_name in REPORT_CALL_DIAGRAMS:
        _render_dot(dot_tool, dot_source, REPORT_FIGURES / f"{diagram_name}.pdf")


def _generate_code2flow(tool: str, dot_tool: str, temporary_dir: Path) -> None:
    for diagram_name, (targets, depth) in CODE2FLOW_DIAGRAMS.items():
        all_nodes: set[str] = set()
        all_edges: set[tuple[str, str]] = set()
        for position, target in enumerate(targets):
            json_output = temporary_dir / f"{diagram_name}-{position}.json"
            _run(
                (
                    tool,
                    str(SOURCE),
                    "--language",
                    "py",
                    "--target-function",
                    target,
                    "--downstream-depth",
                    str(depth),
                    "--output",
                    str(json_output),
                    "--quiet",
                )
            )
            nodes, edges = _read_code2flow_graph(json_output)
            all_nodes.update(nodes)
            all_edges.update(edges)

        _write_call_graph(diagram_name, all_nodes, all_edges, targets, dot_tool)

    # Funções autocontidas são removidas pelo recorte baseado em alvo do
    # Code2flow. Este modo inclui explicitamente as cinco entradas para que as
    # estratégias trivial e vizinho mais próximo também permaneçam visíveis.
    json_output = temporary_dir / "calls-initial-strategies.json"
    _run(
        (
            tool,
            str(SOURCE),
            "--language",
            "py",
            "--no-trimming",
            "--include-only-functions",
            ",".join(STRATEGY_FUNCTIONS),
            "--output",
            str(json_output),
            "--quiet",
        )
    )
    nodes, edges = _read_code2flow_graph(json_output)
    _write_call_graph("calls-initial-strategies", nodes, edges, STRATEGY_ENTRIES, dot_tool)


def _generate_pyreverse(tool: str, dot_tool: str, temporary_dir: Path) -> None:
    domain_sources = (
        SOURCE / "branch_and_bound.py",
        SOURCE / "initial_solutions.py",
        SOURCE / "tsplib.py",
    )
    _run(
        (
            tool,
            "-o",
            "mmd",
            "-p",
            "domain",
            "--source-roots",
            "src",
            "-d",
            str(temporary_dir),
            *(str(path) for path in domain_sources),
        )
    )
    _run(
        (
            tool,
            "-o",
            "mmd",
            "-p",
            "architecture",
            "--source-roots",
            "src",
            "-d",
            str(temporary_dir),
            str(SOURCE),
        )
    )
    _run(
        (
            tool,
            "-o",
            "dot",
            "-p",
            "domain",
            "--source-roots",
            "src",
            "-d",
            str(temporary_dir),
            *(str(path) for path in domain_sources),
        )
    )
    _run(
        (
            tool,
            "-o",
            "dot",
            "-p",
            "architecture",
            "--source-roots",
            "src",
            "-d",
            str(temporary_dir),
            str(SOURCE),
        )
    )

    generated_files = {
        "classes_domain.mmd": "uml-classes.mmd",
        "packages_architecture.mmd": "uml-modules.mmd",
    }
    for source_name, output_name in generated_files.items():
        contents = (temporary_dir / source_name).read_text(encoding="utf-8")
        header = "%% Gerado pelo Pyreverse; não edite manualmente.\n"
        (OUTPUT / output_name).write_text(header + contents, encoding="utf-8", newline="\n")

    dot_files = {
        "classes_domain.dot": "uml-classes",
        "packages_architecture.dot": "uml-modules",
    }
    for source_name, output_stem in dot_files.items():
        dot_source = OUTPUT / f"{output_stem}.dot"
        contents = (temporary_dir / source_name).read_text(encoding="utf-8")
        if output_stem == "uml-modules":
            contents = re.sub(
                r"label=<traveling_salesman_optimization\.([^>]+)>",
                r"label=<\1>",
                contents,
            )
            contents = contents.replace(
                "label=<traveling_salesman_optimization>",
                "label=<package>",
            )
        dot_source.write_text(contents, encoding="utf-8", newline="\n")
        _render_dot(dot_tool, dot_source, REPORT_FIGURES / f"{output_stem}.pdf")


def _embed_in_document() -> None:
    document = ARCHITECTURE_DOC.read_text(encoding="utf-8")
    for diagram_name in EMBEDDED_DIAGRAMS:
        begin = f"<!-- BEGIN GENERATED: {diagram_name} -->"
        end = f"<!-- END GENERATED: {diagram_name} -->"
        diagram = (OUTPUT / f"{diagram_name}.mmd").read_text(encoding="utf-8").strip()
        replacement = f"{begin}\n```mermaid\n{diagram}\n```\n{end}"
        pattern = re.compile(re.escape(begin) + r".*?" + re.escape(end), re.DOTALL)
        document, replacements = pattern.subn(
            lambda _, current=replacement: current,
            document,
        )
        if replacements != 1:
            raise RuntimeError(f"marcadores ausentes ou duplicados para {diagram_name}")
    ARCHITECTURE_DOC.write_text(document, encoding="utf-8", newline="\n")


def main(arguments: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dot",
        type=Path,
        help="caminho opcional para o executável dot do Graphviz",
    )
    args = parser.parse_args(arguments)

    code2flow = _tool_path("code2flow")
    pyreverse = _tool_path("pyreverse")
    dot = str(args.dot.resolve()) if args.dot is not None else _tool_path("dot")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    REPORT_FIGURES.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="tsp-diagrams-") as directory:
        temporary_dir = Path(directory)
        _generate_code2flow(code2flow, dot, temporary_dir)
        _generate_pyreverse(pyreverse, dot, temporary_dir)
    _embed_in_document()
    print(f"Diagramas atualizados em {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
