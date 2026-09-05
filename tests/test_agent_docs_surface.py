"""The drift check of the agent-facing docs.

An agent reads `CLAUDE.md` first. A group that the table omits reads as a
command that does not exist, and the agent writes the code again. The table
drifted twice, so a test holds it to `main.py` instead of a reviewer.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

CLI_ROOT = Path(__file__).resolve().parent.parent
CLAUDE_MD = CLI_ROOT / "CLAUDE.md"
CODE_PATTERNS = CLI_ROOT / ".claude" / "rules" / "code-patterns.md"
COMMANDS = CLI_ROOT / "src" / "ac_cli" / "commands"

_CONSTANT_NAME = re.compile(r"^_[A-Z][A-Z0-9_]*$")


def registered_groups() -> set[str]:
    """Reads every group name that `main.py` mounts on the root app."""
    source = (CLI_ROOT / "src" / "ac_cli" / "main.py").read_text()

    return set(re.findall(r'add_typer\([^)]*name="([^"]+)"', source))


def documented_groups() -> set[str]:
    """Reads the first cell of every row of the Command Groups table."""
    table = CLAUDE_MD.read_text().split("## Command Groups", 1)[1]
    table = table.split("Run `ac <group> --help`", 1)[0]

    return set(re.findall(r"^\| `([a-z-]+)` \|", table, flags=re.MULTILINE))


def path_constants() -> set[str]:
    """Reads every API path prefix constant that `commands/` defines.

    A prefix is a module-level assignment to an upper-case private name. Its
    value is a path literal, or an f-string that starts with another prefix.
    `_DAILY_COST = "daily_cost"` is not a path, so the value decides.
    """
    found: set[str] = set()
    for module in COMMANDS.rglob("*.py"):
        tree = ast.parse(module.read_text())
        for node in tree.body:
            if not isinstance(node, ast.Assign) or len(node.targets) != 1:
                continue
            target = node.targets[0]
            if not isinstance(target, ast.Name):
                continue
            if not _CONSTANT_NAME.match(target.id):
                continue
            if _is_path(node.value):
                found.add(target.id)

    return found


def _is_path(value: ast.expr) -> bool:
    if isinstance(value, ast.Constant):
        return isinstance(value.value, str) and value.value.startswith("/")
    if isinstance(value, ast.JoinedStr) and value.values:
        head = value.values[0]
        if isinstance(head, ast.FormattedValue):
            return isinstance(head.value, ast.Name)

        return isinstance(head, ast.Constant) and str(head.value).startswith("/")

    return False


def documented_constants() -> set[str]:
    """Reads every constant named in the API Route Prefix list."""
    section = CODE_PATTERNS.read_text().split("## API Route Prefix", 1)[1]
    section = section.split("\n## ", 1)[0]

    return set(re.findall(r"`(_[A-Z][A-Z0-9_]*) = ", section))


def test_every_registered_group_has_a_table_row() -> None:
    assert registered_groups() - documented_groups() == set()


def test_the_table_names_no_group_that_main_does_not_register() -> None:
    """The other half of the drift.

    `messaging` and `hooks` outlived their modules and stayed in the table.
    """
    assert documented_groups() - registered_groups() == set()


def test_every_path_constant_is_documented() -> None:
    assert path_constants() - documented_constants() == set()


def test_the_prefix_list_names_no_constant_the_code_dropped() -> None:
    assert documented_constants() - path_constants() == set()
