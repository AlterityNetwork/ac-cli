"""Compares the response keys the CLI reads with the keys each route returns.

The payload check in `audit_payloads.py` proves the CLI sends keys a route
reads. This module proves the CLI reads keys a route returns (ENG-3053). A
renamed response field makes `data.get("old", "?")` print `?` with no error,
so only the spec can catch it.

For each request call, the module follows the response inside the enclosing
function: `resp.json()`, then `.get("key")` and `["key"]` reads, a branch such
as `data if isinstance(data, list) else data.get("data", [])`, a `for` loop
over a list, and the column keys of `print_table` and `print_detail`. Each read
gets the schema of the place it reads from. A read whose schema accepts any
key, or that the module cannot place, is listed as unresolved. It never fails
`--strict`. Runtime reads stay lenient, because a PyPI install runs against
newer APIs; the strictness lives here, in CI.
"""

from __future__ import annotations

import ast
import json
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from pathlib import Path

from audit_payloads import (
    _calls_in,
    _deref,
    _functions,
    _local_nodes,
    _operation_index,
    _request_target,
)

#: Finding kinds that make `--strict` fail.
STRICT_KINDS = frozenset({"RESP-KEY"})

#: Reads the audit accepts although the spec does not list the key, with the
#: reason. Keyed by (method, path, key). The file lists the findings that
#: existed when the audit landed; remove an entry when its read is fixed.
ALLOWLIST_FILE = Path(__file__).with_name("audit_responses_allowlist.json")


def _load_allowed() -> dict[tuple[str, str, str], str]:
    if not ALLOWLIST_FILE.exists():
        return {}
    entries = json.loads(ALLOWLIST_FILE.read_text())
    return {(e["method"], e["path"], e["key"]): e["reason"] for e in entries}


ALLOWED: dict[tuple[str, str, str], str] = _load_allowed()

_TABLE_PRINTERS = {"print_table"}
_DETAIL_PRINTERS = {"print_detail"}

#: One step from the response root: a property name, or "[]" for list items.
_Path = tuple[str, ...]


@dataclass
class ResponseRead:
    """The keys one call reads at one place of its response.

    Attributes:
        method: The HTTP method in upper case.
        path: The normalised API path.
        location: The file under `src/ac_cli` and the line of the call.
        places: The places the keys are read from. A branch gives more than one.
        keys: The keys read there.
    """

    method: str
    path: str
    location: str
    places: frozenset[_Path]
    keys: set[str] = field(default_factory=set)


@dataclass(frozen=True)
class Finding:
    """Keys a call reads that the response of its route does not return."""

    kind: str
    method: str
    path: str
    location: str
    keys: list[str]


def _string(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


class _Flow:
    """Follows the response of one request call inside one function."""

    def __init__(self, function: ast.AST, request: ast.Call) -> None:
        self.nodes = list(_local_nodes(function))
        self.request = request
        self.places: dict[str, set[_Path]] = {}
        self._follow()

    def _response_names(self) -> set[str]:
        names = set()
        for node in self.nodes:
            if isinstance(node, ast.Assign) and node.value is self.request:
                names |= {t.id for t in node.targets if isinstance(t, ast.Name)}
        return names

    def place_of(self, node: ast.AST) -> set[_Path]:
        """The places of the response one expression can hold."""
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "json" and not node.args:
                target = node.func.value
                if target is self.request or (
                    isinstance(target, ast.Name) and target.id in self.responses
                ):
                    return {()}
            if node.func.attr == "get" and node.args:
                key = _string(node.args[0])
                if key is not None:
                    return {(*p, key) for p in self.place_of(node.func.value)}
        if isinstance(node, ast.Subscript):
            key = _string(node.slice)
            if key is not None:
                return {(*p, key) for p in self.place_of(node.value)}
        if isinstance(node, ast.Name):
            return set(self.places.get(node.id, set()))
        if isinstance(node, ast.IfExp):
            return self.place_of(node.body) | self.place_of(node.orelse)
        if isinstance(node, ast.BoolOp):
            found: set[_Path] = set()
            for value in node.values:
                found |= self.place_of(value)
            return found
        return set()

    def _follow(self) -> None:
        self.responses = self._response_names()
        # Assignments can chain (`data` then `items` then a loop), so repeat
        # until no name gains a place.
        changed = True
        while changed:
            changed = False
            for node in self.nodes:
                targets: list[tuple[str, set[_Path]]] = []
                if isinstance(node, ast.Assign):
                    found = self.place_of(node.value)
                    targets = [(t.id, found) for t in node.targets if isinstance(t, ast.Name)]
                elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                    if node.value is not None:
                        targets = [(node.target.id, self.place_of(node.value))]
                elif isinstance(node, ast.For) and isinstance(node.target, ast.Name):
                    found = {(*p, "[]") for p in self.place_of(node.iter)}
                    targets = [(node.target.id, found)]
                for name, found in targets:
                    if found - self.places.get(name, set()):
                        self.places.setdefault(name, set()).update(found)
                        changed = True

    def reads(self) -> dict[frozenset[_Path], set[str]]:
        """The keys read at each place, from `.get`, `[]` and the printers."""
        read: dict[frozenset[_Path], set[str]] = {}

        def add(places: set[_Path], key: str) -> None:
            if places:
                read.setdefault(frozenset(places), set()).add(key)

        for node in self.nodes:
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr == "get" and node.args:
                    key = _string(node.args[0])
                    if key is not None:
                        add(self.place_of(node.func.value), key)
            if isinstance(node, ast.Subscript) and isinstance(node.ctx, ast.Load):
                key = _string(node.slice)
                if key is not None:
                    add(self.place_of(node.value), key)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                printer = node.func.id
                if printer in _TABLE_PRINTERS | _DETAIL_PRINTERS and len(node.args) >= 2:
                    places = self.place_of(node.args[0])
                    if printer in _TABLE_PRINTERS:
                        places = {(*p, "[]") for p in places}
                    for key in _column_keys(node.args[1]):
                        add(places, key)
        return read


def _column_keys(node: ast.AST) -> Iterator[str]:
    """The keys of a `[("key", "Label"), ...]` column list."""
    if isinstance(node, ast.List):
        for item in node.elts:
            if isinstance(item, ast.Tuple) and item.elts:
                key = _string(item.elts[0])
                if key is not None:
                    yield key


def collect_response_reads(root: Path) -> list[ResponseRead]:
    """Reads the response keys every request call under `root` reads.

    Args:
        root: The ac-cli repository root.

    Returns:
        One entry per call and place, in file and line order.
    """
    package = root / "src" / "ac_cli"
    reads: list[ResponseRead] = []
    for module in sorted((package / "commands").rglob("*.py")):
        source = module.read_text()
        tree = ast.parse(source)
        for function in _functions(tree):
            for node in _calls_in(function):
                target = _request_target(node, source)
                if target is None:
                    continue
                location = f"{module.relative_to(package)}:{node.lineno}"
                for places, keys in _Flow(function, node).reads().items():
                    reads.append(ResponseRead(target[0], target[1], location, places, keys))
    reads.sort(key=lambda r: (r.location.split(":")[0], int(r.location.split(":")[1])))
    return reads


def _success_schema(spec: dict, operation: dict) -> dict | None:
    for code, response in sorted(operation.get("responses", {}).items()):
        if code.startswith("2"):
            schema = response.get("content", {}).get("application/json", {}).get("schema")
            if schema is not None:
                return schema
    return None


def _without_null(spec: dict, schema: dict) -> dict | None:
    """The schema, with an `anyOf` of one type and null reduced to that type."""
    schema = _deref(spec, schema)
    for combinator in ("anyOf", "oneOf"):
        if combinator in schema:
            options = [
                _deref(spec, o) for o in schema[combinator] if _deref(spec, o).get("type") != "null"
            ]
            return options[0] if len(options) == 1 else None
    return schema


def _schema_at(spec: dict, root: dict, place: _Path) -> dict | None:
    schema: dict | None = _without_null(spec, root)
    for step in place:
        if schema is None:
            return None
        if step == "[]":
            if schema.get("type") != "array":
                return None
            schema = _without_null(spec, schema.get("items", {}))
        else:
            properties = schema.get("properties")
            if not properties or step not in properties:
                return None
            schema = _without_null(spec, properties[step])
    return schema


def _known_keys(spec: dict, root: dict, place: _Path) -> set[str] | None:
    """The keys the object at `place` returns, or None when no key can be judged."""
    schema = _schema_at(spec, root, place)
    if schema is None or schema.get("type") == "array":
        return None
    properties = schema.get("properties")
    if not properties or schema.get("additionalProperties"):
        return None
    return set(properties)


def _judge(
    spec: dict, read: ResponseRead, allowed: dict | None = None
) -> tuple[set[str], set[str]]:
    """Splits the keys of one read into (unknown, unresolved)."""
    allowed = ALLOWED if allowed is None else allowed
    operation = _operation_index(spec).get((read.method, read.path))
    root = _success_schema(spec, operation[0]) if operation else None
    if root is None:
        return set(), set(read.keys)
    judged = [_known_keys(spec, root, place) for place in read.places]
    known = [k for k in judged if k is not None]
    if not known:
        return set(), set(read.keys)
    # A branch reads one of several places, so a key passes when any place
    # returns it.
    returned = set().union(*known)
    unknown = {key for key in read.keys - returned if (read.method, read.path, key) not in allowed}
    return unknown, set()


def find_unknown_reads(reads: Iterable[ResponseRead], spec: dict) -> list[Finding]:
    """The reads of keys the response of the route does not return."""
    findings = []
    for read in reads:
        unknown, _ = _judge(spec, read)
        if unknown:
            findings.append(
                Finding("RESP-KEY", read.method, read.path, read.location, sorted(unknown))
            )
    return findings


def stale_allowlist(reads: Iterable[ResponseRead], spec: dict) -> list[tuple[str, str, str]]:
    """Allow-list entries no read needs any more: fixed, or now returned."""
    needed = set()
    for read in reads:
        unknown, _ = _judge(spec, read, allowed={})
        needed |= {(read.method, read.path, key) for key in unknown}
    return sorted(set(ALLOWED) - needed)


def unresolved_reads(reads: Iterable[ResponseRead], spec: dict) -> list[ResponseRead]:
    """The reads whose response schema cannot judge a key."""
    out = []
    for read in reads:
        _, unresolved = _judge(spec, read)
        if unresolved:
            out.append(ResponseRead(read.method, read.path, read.location, read.places, unresolved))
    return out


def print_report(reads: list[ResponseRead], spec: dict, findings: list[Finding]) -> None:
    """Prints the findings, the stale allow-list entries and the unresolved reads."""
    print(f"## RESPONSE (keys the CLI reads that the route does not return): {len(findings)}")
    for f in findings:
        print(f"  {f.kind:15s} {f.method:6s} {f.path} {', '.join(f.keys)}  [{f.location}]")
    print()
    stale = stale_allowlist(reads, spec)
    print(f"## RESPONSE-ALLOWLIST-STALE (remove from {ALLOWLIST_FILE.name}): {len(stale)}")
    for method, path, key in stale:
        print(f"  {method:6s} {path} {key}")
    print()
    unresolved = unresolved_reads(reads, spec)
    print(f"## RESPONSE-UNRESOLVED (untyped response; never fails --strict): {len(unresolved)}")
    for r in unresolved:
        print(f"  {r.method:6s} {r.path} {', '.join(sorted(r.keys))}  [{r.location}]")
