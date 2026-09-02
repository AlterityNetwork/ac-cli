"""Guards the two ways one command group silently loses a command.

ENG-2276 and ENG-2286 added commands to `ac agentic capabilities` at the same
time. Git merged the two branches with no conflict, and the result was wrong:
the module held `capabilities_app = typer.Typer(...)` twice, so the second
object replaced the first and every command registered on the first was gone.
Nothing raised, because rebinding a module-level name is legal Python.

One test reads the source, because a replaced object leaves no trace in the
built application. The other walks the built application, because a duplicate
command name is invisible in the source when the two sit in different modules.
"""

import ast
from collections import Counter
from pathlib import Path

import typer

from ac_cli.main import app as root_app

COMMANDS_DIR = Path(__file__).resolve().parent.parent / "src" / "ac_cli" / "commands"


def _modules() -> list[Path]:
    """Answers every command module, so a new one is guarded on the day it lands.

    The two readers below key their report on the path relative to this
    directory, and never on `Path.name`. Eleven files are called `__init__.py`,
    so the bare name would report one package and hide the rest.

    ⚠️ **`__init__.py` is included, and it is where the fault is most likely.**
    Each package `__init__.py` builds its own group and registers the children:
    `crm/` makes eleven `add_typer` calls and `admin/` fourteen. A merge that
    repeats one of those lines lands there, not in a leaf module.
    """
    return sorted(COMMANDS_DIR.rglob("*.py"))


def _typer_bindings(tree: ast.AST) -> list[str]:
    """Names every module-level binding of a `typer.Typer(...)` call."""
    # `iter_child_nodes` and not `ast.walk`. The walk reaches into every
    # function and class body, so a group built inside a helper would count as
    # a second binding of the module-level name and fail this guard for a file
    # that holds one.
    return [
        target.id
        for node in ast.iter_child_nodes(tree)
        if isinstance(node, ast.Assign)
        and isinstance(node.value, ast.Call)
        and getattr(node.value.func, "attr", None) == "Typer"
        for target in node.targets
        if isinstance(target, ast.Name)
    ]


def _add_typer_names(tree: ast.AST) -> list[str]:
    """Names every group an `add_typer(..., name=...)` call registers."""
    return [
        keyword.value.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and getattr(node.func, "attr", None) == "add_typer"
        for keyword in node.keywords
        if keyword.arg == "name"
        and isinstance(keyword.value, ast.Constant)
        and isinstance(keyword.value.value, str)
    ]


def test_each_typer_group_is_built_once_per_module() -> None:
    """A second `x_app = typer.Typer(...)` discards every command on the first.

    This is the exact shape the ENG-2276 and ENG-2286 merge produced. It is
    read from the source, because the discarded object leaves no trace: the
    module imports, the surviving commands work, and the lost ones are simply
    absent.
    """
    rebound = {}
    for module in _modules():
        repeated = [
            name
            for name, count in Counter(
                _typer_bindings(ast.parse(module.read_text(encoding="utf-8")))
            ).items()
            if count > 1
        ]
        if repeated:
            rebound[str(module.relative_to(COMMANDS_DIR))] = repeated

    assert not rebound, f"these modules build one Typer group twice: {rebound}"


def test_each_group_name_is_registered_once_per_module() -> None:
    """Two `add_typer` calls under one name leave the second unreachable."""
    repeated = {}
    for module in _modules():
        names = [
            name
            for name, count in Counter(
                _add_typer_names(ast.parse(module.read_text(encoding="utf-8")))
            ).items()
            if count > 1
        ]
        if names:
            repeated[str(module.relative_to(COMMANDS_DIR))] = names

    assert not repeated, f"these modules register one group name twice: {repeated}"


def _walk(group: typer.Typer, path: str) -> list[tuple[str, str]]:
    """Answers every `(group path, command name)` the built application holds."""
    found = [
        (path, command.name or (command.callback.__name__ if command.callback else "?"))
        for command in group.registered_commands
    ]
    for child in group.registered_groups:
        if child.typer_instance is not None:
            found.extend(_walk(child.typer_instance, f"{path} {child.name}"))
    return found


def test_no_two_commands_claim_one_name_in_one_group() -> None:
    """Click keeps one command per name, so a second one never runs.

    The source guards above cannot see this: two modules may each register a
    `list` command onto the same imported group, and neither file repeats a
    name. Only the built tree shows the collision.
    """
    repeated = sorted(pair for pair, count in Counter(_walk(root_app, "ac")).items() if count > 1)

    assert not repeated, f"these commands are claimed twice: {repeated}"
