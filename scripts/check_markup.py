#!/usr/bin/env python3
"""Fail when a print call gives the markup parser text the CLI did not write.

`rprint` and `console.print` read rich markup in a str argument. A value the
CLI did not write — a CRM name, a mail body, an MCP tool description — that
holds `[/beta]` raises MarkupError, so the command exits 1 with no output. One
that holds `[urgent]` exits 0 without the bracketed word, so the reader reads a
value the record does not hold.

Every print argument must therefore be one of:

- a str literal, which the call site wrote
- `as_text(value)`, which prints the value as it is
- `styled("[green]...{}", value)`, where the template is the markup the call
  site wrote and each value prints as it is
- a renderable the parser never reads: `Text`, `Table`, `Pretty`
- a name, an `a if b else c` or an `a + b` built only from those

A grep does not find these. ENG-2134 shipped a false scope claim from one, and
an AST walk then found a hand-built Table, two multi-line calls and one
unwrapped variable beside a wrapped one. This walks the tree instead.

Usage:
    python scripts/check_markup.py [path ...]      # default: src/ac_cli
"""

from __future__ import annotations

import ast
import pathlib
import sys

# The calls that read markup. `rprint` is `rich.print`, and the CLI imports it
# under that name in every command module.
PRINT_NAMES = {"rprint"}
PRINT_ATTRS = {"print"}

# The wrappers that answer a renderable the markup parser never reads.
SAFE_CALLS = {"as_text", "styled", "Text", "Table", "Pretty"}

# The keyword arguments of print that carry text. `sep` and `end` reach the
# same parser as a positional argument does.
TEXT_KEYWORDS = {"sep", "end"}


class _Checker(ast.NodeVisitor):
    """Reads one module, and collects one failure for each unsafe argument."""

    def __init__(self, path: pathlib.Path) -> None:
        self.path = path
        self.failures: list[tuple[int, str]] = []
        # name -> the expressions assigned to it, for the whole module. A name
        # is checked against every assignment, so a name that is safe on one
        # branch and unsafe on another fails.
        self.bindings: dict[str, list[ast.expr]] = {}

    def collect_bindings(self, tree: ast.Module) -> None:
        """Records every value bound to a name, and every value appended to it.

        A call site builds a Table or a line of options over several
        statements, then prints the name. The name is safe when each of those
        values is.
        """
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        self.bindings.setdefault(target.id, []).append(node.value)
            elif isinstance(node, ast.AnnAssign):
                if isinstance(node.target, ast.Name) and node.value is not None:
                    self.bindings.setdefault(node.target.id, []).append(node.value)
            elif isinstance(node, ast.AugAssign):
                if isinstance(node.target, ast.Name):
                    self.bindings.setdefault(node.target.id, []).append(node.value)
            elif isinstance(node, ast.Call):
                # parts.append(value)
                func = node.func
                if (
                    isinstance(func, ast.Attribute)
                    and func.attr in {"append", "extend"}
                    and isinstance(func.value, ast.Name)
                    and node.args
                ):
                    self.bindings.setdefault(func.value.id, []).append(node.args[0])

    def visit_Call(self, node: ast.Call) -> None:  # noqa: N802 - the ast API
        if self._is_print(node):
            for arg in node.args:
                if isinstance(arg, ast.Starred):
                    self._check(arg.value, node.lineno, set())
                else:
                    self._check(arg, node.lineno, set())
            for kw in node.keywords:
                if kw.arg in TEXT_KEYWORDS:
                    self._check(kw.value, node.lineno, set())
        self.generic_visit(node)

    @staticmethod
    def _is_print(node: ast.Call) -> bool:
        func = node.func
        if isinstance(func, ast.Name):
            return func.id in PRINT_NAMES
        return isinstance(func, ast.Attribute) and func.attr in PRINT_ATTRS

    def _fail(self, node: ast.AST, lineno: int, source: ast.expr) -> None:
        self.failures.append((lineno, ast.unparse(source)[:88]))

    def _check(self, node: ast.expr, lineno: int, seen: set[str]) -> None:
        """Adds a failure when this argument can reach the markup parser.

        Args:
            node: The argument, or a value bound to a name the print reads.
            lineno: The line of the print call, which is what a reader fixes.
            seen: The names already followed, so a cycle ends.
        """
        if isinstance(node, ast.Constant):
            # A str literal is text the call site wrote. Any other constant
            # (a number, a None) never holds a bracket.
            return

        if isinstance(node, ast.Call):
            func = node.func
            name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", "")
            if name in SAFE_CALLS:
                if name == "styled" and node.args and not isinstance(node.args[0], ast.Constant):
                    # A template that is not a literal is text from somewhere
                    # else, and that is the fault this check exists for.
                    self._check(node.args[0], lineno, seen)
                return
            self._fail(node, lineno, node)
            return

        if isinstance(node, ast.IfExp):
            self._check(node.body, lineno, seen)
            self._check(node.orelse, lineno, seen)
            return

        if isinstance(node, ast.BoolOp):
            for value in node.values:
                self._check(value, lineno, seen)
            return

        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            self._check(node.left, lineno, seen)
            self._check(node.right, lineno, seen)
            return

        if isinstance(node, (ast.List, ast.Tuple)):
            for element in node.elts:
                self._check(element, lineno, seen)
            return

        if isinstance(node, ast.Name):
            if node.id in seen:
                return
            values = self.bindings.get(node.id)
            if not values:
                self._fail(node, lineno, node)
                return
            for value in values:
                self._check(value, lineno, seen | {node.id})
            return

        # A JoinedStr, a subscript, an attribute: every one can carry a value
        # the CLI did not write, and the parser reads all of them.
        self._fail(node, lineno, node)


def check(path: pathlib.Path) -> list[str]:
    """Answers one message for each unsafe print argument in one file."""
    tree = ast.parse(path.read_text())
    checker = _Checker(path)
    checker.collect_bindings(tree)
    checker.visit(tree)
    return [f"{path}:{line}: unwrapped print argument — {src}" for line, src in checker.failures]


def main(argv: list[str]) -> int:
    targets = [pathlib.Path(a) for a in argv[1:]] or [pathlib.Path("src/ac_cli")]
    messages: list[str] = []
    for target in targets:
        files = sorted(target.rglob("*.py")) if target.is_dir() else [target]
        for file in files:
            messages += check(file)
    for message in messages:
        print(message)
    if messages:
        print(
            f"\n{len(messages)} print argument(s) reach the rich markup parser.\n"
            "Wrap each value in as_text(), or write the line with styled().",
            file=sys.stderr,
        )
        return 1
    print(f"markup check: {len(targets)} target(s) clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
