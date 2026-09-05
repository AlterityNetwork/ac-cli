#!/usr/bin/env python3
"""Fail when a print call gives the markup parser text the CLI did not write.

`rprint` and `console.print` read rich markup in a str. A value the CLI did
not write — a CRM name, a mail body, an MCP tool description — that holds
`[/beta]` raises MarkupError, so the command exits 1 with no output. One that
holds `[urgent]` exits 0 without the bracketed word, so the reader reads a
value the record does not hold. `Table.add_row` reads the same parser.

Every such argument must be one of:

- a str literal, which the call site wrote
- `as_text(value)`, which prints the value as it is
- `styled("[green]...{}", value)`, where the template is the markup the call
  site wrote and each value prints as it is
- a renderable the parser never reads: `Text`, `Table`, `Pretty`, `_cell`
- a name, an `a if b else c` or an `a + b` built only from those

The check also reads the value count of a `styled` call. A count that does not
match raises ValueError, so the command exits 1 with no output — the same
fault, from the helper that closes it.

`add_column` is not checked. A header is the label side, and every call site
passes a literal. See print_table in formatting.py.

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

from rich.text import Text

# `rprint` is `rich.print`, and the CLI imports it under that name in every
# command module. `<console>.print` and `<table>.add_row` reach the same
# parser.
PRINT_NAMES = {"rprint"}
PRINT_ATTRS = {"print", "add_row"}

# The wrappers that answer a renderable the markup parser never reads.
SAFE_CALLS = {"as_text", "styled", "Text", "Table", "Pretty", "_cell"}

# The keyword arguments of print that carry text. `sep` and `end` reach the
# same parser as a positional argument does.
TEXT_KEYWORDS = {"sep", "end"}

# The scopes that hold their own names. A comprehension holds its target too,
# but that target never leaves it.
_SCOPE_NODES = (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)

# A name that is bound, where the value cannot be read: a parameter, a loop
# target, a `with ... as`, an unpacking, an import, an `except ... as`. Each
# can hold a value the CLI did not write, so each fails.
UNREADABLE = None


class _Scope:
    """One namespace, and the values bound to each name in it."""

    def __init__(self, parent: _Scope | None) -> None:
        self.parent = parent
        self.bindings: dict[str, list[ast.expr | None]] = {}

    def bind(self, name: str, value: ast.expr | None) -> None:
        self.bindings.setdefault(name, []).append(value)

    def resolve(self, name: str) -> list[ast.expr | None] | None:
        """Answers the values of the nearest scope that binds the name.

        A name is read in one scope only. Reading the whole module instead
        lets a parameter borrow the safety of a same-named module constant.
        """
        scope: _Scope | None = self
        while scope is not None:
            if name in scope.bindings:
                return scope.bindings[name]
            scope = scope.parent
        return None


def _targets(node: ast.expr) -> list[str]:
    """Answers each Name a binding target holds, through a tuple or a list."""
    if isinstance(node, ast.Name):
        return [node.id]
    if isinstance(node, (ast.Tuple, ast.List)):
        return [name for element in node.elts for name in _targets(element)]
    if isinstance(node, ast.Starred):
        return _targets(node.value)
    return []


def _own_nodes(scope_node: ast.AST):
    """Walks one scope, and stops at the body of a scope inside it.

    A lambda yields its body only. Its arguments are names it binds, and
    _build_scope has already read them.
    """
    fields = (
        [("body", scope_node.body)]
        if isinstance(scope_node, ast.Lambda)
        else ast.iter_fields(scope_node)
    )
    for field, value in fields:
        children = value if isinstance(value, list) else [value]
        for child in children:
            if not isinstance(child, ast.AST):
                continue
            if isinstance(child, _SCOPE_NODES):
                # The definition binds its own name in this scope. Its body
                # does not.
                continue
            yield child
            yield from _own_nodes(child)


def _build_scope(scope_node: ast.AST, parent: _Scope | None) -> _Scope:
    """Records every name this scope binds, and the value bound to it."""
    scope = _Scope(parent)

    if isinstance(scope_node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
        args = scope_node.args
        for arg in [*args.posonlyargs, *args.args, *args.kwonlyargs]:
            scope.bind(arg.arg, UNREADABLE)
        for arg in (args.vararg, args.kwarg):
            if arg is not None:
                scope.bind(arg.arg, UNREADABLE)

    for node in _own_nodes(scope_node):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    scope.bind(target.id, node.value)
                else:
                    for name in _targets(target):
                        scope.bind(name, UNREADABLE)
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name):
                scope.bind(node.target.id, node.value)
        elif isinstance(node, ast.AugAssign):
            if isinstance(node.target, ast.Name):
                scope.bind(node.target.id, node.value)
        elif isinstance(node, ast.NamedExpr):
            if isinstance(node.target, ast.Name):
                scope.bind(node.target.id, node.value)
        elif isinstance(node, (ast.For, ast.AsyncFor)):
            for name in _targets(node.target):
                scope.bind(name, UNREADABLE)
        elif isinstance(node, ast.withitem):
            if node.optional_vars is not None:
                for name in _targets(node.optional_vars):
                    scope.bind(name, UNREADABLE)
        elif isinstance(node, ast.ExceptHandler):
            if node.name:
                scope.bind(node.name, UNREADABLE)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                scope.bind(alias.asname or alias.name.split(".")[0], UNREADABLE)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            scope.bind(node.name, UNREADABLE)
        elif isinstance(node, ast.Call):
            # parts.append(value) / parts.extend([value])
            func = node.func
            if (
                isinstance(func, ast.Attribute)
                and func.attr in {"append", "extend"}
                and isinstance(func.value, ast.Name)
                and node.args
            ):
                scope.bind(func.value.id, node.args[0])
    return scope


class _Checker:
    """Reads one module, and collects one failure for each unsafe argument."""

    def __init__(self) -> None:
        self.failures: list[tuple[int, str]] = []

    def run(self, tree: ast.Module) -> None:
        self._walk(tree, _build_scope(tree, None))

    def _walk(self, scope_node: ast.AST, scope: _Scope) -> None:
        for node in _own_nodes(scope_node):
            if isinstance(node, ast.Call) and self._is_print(node):
                self._check_call(node, scope)
        for node in self._child_scopes(scope_node):
            self._walk(node, _build_scope(node, scope))

    @staticmethod
    def _child_scopes(scope_node: ast.AST):
        """Answers the scopes defined directly inside this one."""
        fields = (
            [("body", scope_node.body)]
            if isinstance(scope_node, ast.Lambda)
            else ast.iter_fields(scope_node)
        )
        for field, value in fields:
            children = value if isinstance(value, list) else [value]
            for child in children:
                if isinstance(child, _SCOPE_NODES):
                    yield child
                elif isinstance(child, ast.AST):
                    yield from _Checker._child_scopes(child)

    @staticmethod
    def _is_print(node: ast.Call) -> bool:
        func = node.func
        if isinstance(func, ast.Name):
            return func.id in PRINT_NAMES
        return isinstance(func, ast.Attribute) and func.attr in PRINT_ATTRS

    def _check_call(self, node: ast.Call, scope: _Scope) -> None:
        for arg in node.args:
            target = arg.value if isinstance(arg, ast.Starred) else arg
            self._check(target, node.lineno, scope, set())
        for keyword in node.keywords:
            if keyword.arg in TEXT_KEYWORDS:
                self._check(keyword.value, node.lineno, scope, set())

    def _fail(self, lineno: int, source: ast.expr, why: str) -> None:
        self.failures.append((lineno, f"{why} — {ast.unparse(source)[:88]}"))

    def _check_places(self, node: ast.Call, template: str, lineno: int) -> None:
        """Fails when a styled call cannot fill its own template.

        A wrong count raises ValueError at run time, and the command then
        exits 1 with no output. That is the fault this file exists to stop.

        The count is read the way styled reads it, and not by counting `{}`.
        The two disagree for a `{}` inside a tag: `[link={}]{}[/link]` holds
        two of them, and the parser eats the first into the tag. That call
        site raises, and a count of `{}` alone calls it well formed.

        Args:
            node: The styled call, where args[0] is the template.
            template: The literal template.
            lineno: The line of the print call, which is what a reader fixes.
        """
        places = Text.from_markup(template.replace("{}", "\x00")).plain.count("\x00")
        if places != template.count("{}"):
            self._fail(lineno, node, "styled() has a {} inside a tag, which is not a place")
            return
        values = len(node.args) - 1
        if places != values:
            self._fail(lineno, node, f"styled() takes {places} value(s) here, and got {values}")

    def _check(self, node: ast.expr, lineno: int, scope: _Scope, seen: set[str]) -> None:
        """Adds a failure when this argument can reach the markup parser.

        Args:
            node: The argument, or a value bound to a name the print reads.
            lineno: The line of the print call, which is what a reader fixes.
            scope: The namespace the print reads its names in.
            seen: The names already followed, so a cycle ends.
        """
        if isinstance(node, ast.Constant):
            # A str literal is text the call site wrote. Any other constant
            # (a number, a None) never holds a bracket.
            return

        if isinstance(node, ast.Call):
            func = node.func
            name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", "")
            if name not in SAFE_CALLS:
                self._fail(lineno, node, "unwrapped print argument")
                return
            if name == "styled" and node.args:
                template = node.args[0]
                if not isinstance(template, ast.Constant) or not isinstance(template.value, str):
                    self._check(template, lineno, scope, seen)
                    return
                self._check_places(node, template.value, lineno)
            return

        if isinstance(node, ast.IfExp):
            self._check(node.body, lineno, scope, seen)
            self._check(node.orelse, lineno, scope, seen)
            return

        if isinstance(node, ast.BoolOp):
            for value in node.values:
                self._check(value, lineno, scope, seen)
            return

        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            self._check(node.left, lineno, scope, seen)
            self._check(node.right, lineno, scope, seen)
            return

        if isinstance(node, (ast.List, ast.Tuple)):
            for element in node.elts:
                self._check(element, lineno, scope, seen)
            return

        if isinstance(node, (ast.GeneratorExp, ast.ListComp)):
            # A comprehension holds its own targets, and each one can carry a
            # value the CLI did not write. Read the element in a scope that
            # binds them, so a target never borrows an enclosing name.
            inner = _Scope(scope)
            for generator in node.generators:
                for name in _targets(generator.target):
                    inner.bind(name, UNREADABLE)
            self._check(node.elt, lineno, inner, seen)
            return

        if isinstance(node, ast.Name):
            if node.id in seen:
                return
            values = scope.resolve(node.id)
            if not values:
                self._fail(lineno, node, "unwrapped print argument")
                return
            for value in values:
                if value is UNREADABLE:
                    self._fail(lineno, node, "unwrapped print argument")
                    continue
                self._check(value, lineno, scope, seen | {node.id})
            return

        # A JoinedStr, a subscript, an attribute: every one can carry a value
        # the CLI did not write, and the parser reads all of them.
        self._fail(lineno, node, "unwrapped print argument")


def check(path: pathlib.Path) -> list[str]:
    """Answers one message for each unsafe print argument in one file."""
    checker = _Checker()
    checker.run(ast.parse(path.read_text()))
    # A name that two loops bind fails twice for one argument. One argument is
    # one fix, so report it once.
    return [f"{path}:{line}: {message}" for line, message in sorted(set(checker.failures))]


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
