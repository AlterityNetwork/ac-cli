"""Compares the fields the CLI sends with the fields each API route reads.

The path check in `audit_endpoints.py` proves that a route exists. This module
proves that each call sends keys the route accepts. FastAPI drops an unknown
body field or query parameter with no error. A misspelt key is therefore a
silent no-op, and the path check cannot see it.

The CLI side comes from the syntax tree of each command module. For each
request call, the module follows the `json=` and `params=` values inside the
enclosing function: dict literals, `_build_body(...)` keywords, subscript
stores, `update` and `setdefault`. A value it cannot follow is listed as
unresolved. Check an unresolved call by hand. It never fails `--strict`.

The API side comes from the OpenAPI spec: the request body schema and the
query parameters of each operation.
"""

from __future__ import annotations

import ast
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from audit_endpoints import _normalize, _resolve_cli_path

_METHODS = {"get", "post", "put", "patch", "delete"}
_BODY_BUILDERS = {"_build_body", "dict"}
_JSON_MEDIA = "application/json"

#: Finding kinds that make `--strict` fail.
STRICT_KINDS = frozenset({"BODY-KEY", "BODY-UNEXPECTED", "BODY-MISSING", "QUERY-KEY", "DEPRECATED"})


@dataclass
class CliCall:
    """One request call in a command module.

    Attributes:
        method: The HTTP method in upper case.
        path: The normalised API path.
        location: The file under `src/ac_cli` and the line of the call.
        body_keys: The JSON body keys the call can send. None when the call
          sends no `json=` value.
        query_keys: The query parameter names the call can send. None when the
          call sends no `params=` value.
        unresolved: The arguments the module could not follow, as source text.
    """

    method: str
    path: str
    location: str
    body_keys: set[str] | None
    query_keys: set[str] | None
    unresolved: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Finding:
    """One mismatch between a CLI call and the route it calls.

    Attributes:
        kind: The finding kind. `STRICT_KINDS` lists the kinds that fail.
        method: The HTTP method.
        path: The normalised API path.
        location: Where the call is.
        keys: The keys the finding is about, sorted.
    """

    kind: str
    method: str
    path: str
    location: str
    keys: list[str]


class _Keys:
    """Collects keys and records whether the collection is complete."""

    def __init__(self) -> None:
        self.keys: set[str] = set()
        self.complete = True

    def merge(self, other: _Keys) -> None:
        self.keys |= other.keys
        self.complete = self.complete and other.complete


def _local_nodes(function: ast.AST) -> Iterator[ast.AST]:
    """Yields the nodes of one function, without nested functions."""
    stack = list(ast.iter_child_nodes(function))
    while stack:
        node = stack.pop()
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            continue
        yield node
        stack.extend(ast.iter_child_nodes(node))


#: Top-level functions of the command modules, by name. A name that more than
#: one module defines maps to None, because the call cannot be matched.
_Helpers = dict[str, ast.FunctionDef | None]


class _Resolver:
    """Follows a dict value inside one function."""

    def __init__(self, function: ast.AST, request: ast.Call | None, helpers: _Helpers) -> None:
        self.nodes = list(_local_nodes(function))
        self.request = request
        self.helpers = helpers

    def keys(self, node: ast.AST | None, seen: frozenset[str] = frozenset()) -> _Keys:
        result = _Keys()
        if node is None or (isinstance(node, ast.Constant) and node.value is None):
            return result
        if isinstance(node, ast.Dict):
            for key, value in zip(node.keys, node.values, strict=True):
                if key is None:
                    result.merge(self.keys(value, seen))
                elif isinstance(key, ast.Constant) and isinstance(key.value, str):
                    result.keys.add(key.value)
                else:
                    result.complete = False
            return result
        if isinstance(node, ast.Call) and _call_name(node) in _BODY_BUILDERS:
            for arg in node.args:
                result.merge(self.keys(arg, seen))
            for keyword in node.keywords:
                if keyword.arg is None:
                    result.merge(self.keys(keyword.value, seen))
                else:
                    result.keys.add(keyword.arg)
            return result
        if isinstance(node, ast.IfExp):
            result.merge(self.keys(node.body, seen))
            result.merge(self.keys(node.orelse, seen))
            return result
        if isinstance(node, ast.BoolOp):
            for value in node.values:
                result.merge(self.keys(value, seen))
            return result
        if isinstance(node, ast.Name) and node.id not in seen:
            return self._name_keys(node.id, seen | {node.id})
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            helper = self.helpers.get(node.func.id)
            marker = f"def {node.func.id}"
            if helper is not None and marker not in seen:
                return self._helper_keys(helper, seen | {marker})
        result.complete = False
        return result

    def _helper_keys(self, helper: ast.FunctionDef, seen: frozenset[str]) -> _Keys:
        """Reads the keys of every dict that one helper function returns."""
        inner = _Resolver(helper, None, self.helpers)
        result = _Keys()
        returns = [n for n in inner.nodes if isinstance(n, ast.Return)]
        if not returns:
            result.complete = False
        for node in returns:
            result.merge(inner.keys(node.value, seen))
        return result

    def _name_keys(self, name: str, seen: frozenset[str]) -> _Keys:
        result = _Keys()
        assigned = False
        for node in self.nodes:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == name:
                        assigned = True
                        result.merge(self.keys(node.value, seen))
                    elif _is_subscript_of(target, name):
                        result.merge(self._subscript_key(target))
            elif isinstance(node, ast.AnnAssign) and _is_name(node.target, name):
                if node.value is not None:
                    assigned = True
                    result.merge(self.keys(node.value, seen))
            elif isinstance(node, ast.AugAssign) and _is_name(node.target, name):
                result.merge(self.keys(node.value, seen))
            elif isinstance(node, ast.Call):
                result.merge(self._call_effect(node, name, seen))
        if not assigned:
            result.complete = False
        return result

    def _subscript_key(self, node: ast.Subscript) -> _Keys:
        """Reads the key of `name[key] = ...`.

        The key is a constant, or a loop variable that takes constant values
        from a tuple of tuples, as in `for key, value in (("a", a),): ...`.
        """
        if not isinstance(node.slice, ast.Name):
            return _constant_key(node.slice)
        for loop in self.nodes:
            if isinstance(loop, ast.For):
                keys = _loop_constants(loop, node.slice.id)
                if keys is not None:
                    return keys
        return _constant_key(node.slice)

    def _call_effect(self, node: ast.Call, name: str, seen: frozenset[str]) -> _Keys:
        """Reads what one call does to the dict `name`."""
        result = _Keys()
        func = node.func
        if isinstance(func, ast.Attribute) and _is_name(func.value, name):
            if func.attr == "update":
                for arg in node.args:
                    result.merge(self.keys(arg, seen))
                for keyword in node.keywords:
                    if keyword.arg is None:
                        result.merge(self.keys(keyword.value, seen))
                    else:
                        result.keys.add(keyword.arg)
            elif func.attr == "setdefault" and node.args:
                result.merge(_constant_key(node.args[0]))
            return result
        if node is self.request:
            return result
        passed = [*node.args, *(k.value for k in node.keywords)]
        if any(_is_name(arg, name) for arg in passed):
            # Another function receives the dict and can add keys to it.
            result.complete = False
        return result


def _is_name(node: ast.AST, name: str) -> bool:
    return isinstance(node, ast.Name) and node.id == name


def _is_subscript_of(node: ast.AST, name: str) -> bool:
    return isinstance(node, ast.Subscript) and _is_name(node.value, name)


def _constant_key(node: ast.AST) -> _Keys:
    result = _Keys()
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        result.keys.add(node.value)
    else:
        result.complete = False
    return result


def _loop_constants(loop: ast.For, name: str) -> _Keys | None:
    """Reads the constant values one loop variable takes.

    Returns:
        The values, or None when the loop does not bind `name`.
    """
    target = loop.target
    if isinstance(target, ast.Name):
        position = 0 if target.id == name else None
        rows = [[item] for item in getattr(loop.iter, "elts", [])]
    elif isinstance(target, ast.Tuple):
        names = [t.id if isinstance(t, ast.Name) else None for t in target.elts]
        position = names.index(name) if name in names else None
        rows = [getattr(item, "elts", []) for item in getattr(loop.iter, "elts", [])]
    else:
        return None
    if position is None:
        return None
    result = _Keys()
    if not isinstance(loop.iter, (ast.Tuple, ast.List)):
        result.complete = False
        return result
    for row in rows:
        result.merge(_constant_key(row[position]) if len(row) > position else _Keys())
    return result


def _call_name(node: ast.Call) -> str | None:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return None


def _request_target(node: ast.Call, source: str) -> tuple[str, str] | None:
    """Reads the method and the path of one request call."""
    func = node.func
    if isinstance(func, ast.Name) and func.id == "_api_request":
        method_arg, path_args = (node.args[:1], node.args[1:2])
    elif (
        isinstance(func, ast.Attribute)
        and _is_name(func.value, "client")
        and func.attr == "request"
    ):
        method_arg, path_args = (node.args[:1], node.args[1:2])
    elif (
        isinstance(func, ast.Attribute) and _is_name(func.value, "client") and func.attr in _METHODS
    ):
        method_arg, path_args = ([], node.args[:1])
        method = func.attr
    else:
        return None
    if method_arg:
        first = method_arg[0]
        if not (isinstance(first, ast.Constant) and isinstance(first.value, str)):
            return None
        method = first.value
    if method.lower() not in _METHODS or not path_args:
        return None
    raw = ast.get_source_segment(source, path_args[0])
    resolved = _resolve_cli_path(raw) if raw else None
    if resolved is None:
        return None
    return method.upper(), _normalize(resolved)


def _functions(tree: ast.AST) -> Iterator[ast.AST]:
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield node


def _calls_in(function: ast.AST) -> Iterator[ast.Call]:
    for node in _local_nodes(function):
        if isinstance(node, ast.Call):
            yield node


def collect_cli_payloads(root: Path) -> list[CliCall]:
    """Reads every request call in the command modules under `root`.

    Args:
        root: The ac-cli repository root.

    Returns:
        One entry per request call whose path resolves, in file and line
        order.
    """
    package = root / "src" / "ac_cli"
    modules = {
        module: module.read_text() for module in sorted((package / "commands").rglob("*.py"))
    }
    trees = {module: ast.parse(source) for module, source in modules.items()}
    helpers: _Helpers = {}
    for tree in trees.values():
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                helpers[node.name] = None if node.name in helpers else node
    calls: list[CliCall] = []
    for module, source in modules.items():
        # A helper in the same module wins over a name another module shares.
        local = {
            node.name: node for node in trees[module].body if isinstance(node, ast.FunctionDef)
        }
        visible = {**helpers, **local}
        for function in _functions(trees[module]):
            for node in _calls_in(function):
                target = _request_target(node, source)
                if target is None:
                    continue
                resolver = _Resolver(function, node, visible)
                calls.append(_read_call(node, resolver, source, target, module, package))
    calls.sort(key=lambda c: (c.location.split(":")[0], int(c.location.split(":")[1])))
    return calls


def _read_call(
    node: ast.Call,
    resolver: _Resolver,
    source: str,
    target: tuple[str, str],
    module: Path,
    package: Path,
) -> CliCall:
    found: dict[str, set[str] | None] = {"json": None, "params": None}
    unresolved: list[str] = []
    for keyword in node.keywords:
        text = f"{keyword.arg}={ast.get_source_segment(source, keyword.value)}"
        if keyword.arg in found:
            keys = resolver.keys(keyword.value)
            found[keyword.arg] = keys.keys
            if not keys.complete:
                unresolved.append(text)
        elif keyword.arg in {"data", "files", "content"}:
            unresolved.append(text)
    return CliCall(
        method=target[0],
        path=target[1],
        location=f"{module.relative_to(package)}:{node.lineno}",
        body_keys=found["json"],
        query_keys=found["params"],
        unresolved=unresolved,
    )


def _deref(spec: dict, schema: dict) -> dict:
    seen: set[str] = set()
    while "$ref" in schema and schema["$ref"] not in seen:
        seen.add(schema["$ref"])
        node: Any = spec
        for part in schema["$ref"].lstrip("#/").split("/"):
            node = node.get(part, {})
        schema = node
    return schema


def _schema_fields(spec: dict, schema: dict) -> tuple[set[str], set[str]] | None:
    """Reads the properties and the required keys of one object schema.

    Returns:
        The property names and the required names, or None when the schema
        accepts free-form keys and no key can be judged.
    """
    schema = _deref(spec, schema)
    for combinator in ("anyOf", "oneOf"):
        if combinator in schema:
            options = [
                _schema_fields(spec, option)
                for option in schema[combinator]
                if _deref(spec, option).get("type") != "null"
            ]
            if not options or any(option is None for option in options):
                return None
            names = set().union(*(o[0] for o in options if o))
            required = set.intersection(*(o[1] for o in options if o))
            return names, required
    if "allOf" in schema:
        names: set[str] = set(schema.get("properties", {}))
        required: set[str] = set(schema.get("required", []))
        for part in schema["allOf"]:
            fields = _schema_fields(spec, part)
            if fields is None:
                return None
            names |= fields[0]
            required |= fields[1]
        return names, required
    if "properties" not in schema or schema.get("additionalProperties"):
        return None
    return set(schema["properties"]), set(schema.get("required", []))


def _operation_index(spec: dict) -> dict[tuple[str, str], tuple[dict, list[dict]]]:
    index: dict[tuple[str, str], tuple[dict, list[dict]]] = {}
    for raw, item in spec.get("paths", {}).items():
        shared = item.get("parameters", [])
        for method, operation in item.items():
            if method in _METHODS:
                key = (method.upper(), _normalize(raw))
                index.setdefault(key, (operation, shared))
    return index


def _query_names(spec: dict, operation: dict, shared: list[dict]) -> set[str]:
    names = set()
    for parameter in [*shared, *operation.get("parameters", [])]:
        parameter = _deref(spec, parameter)
        if parameter.get("in") == "query":
            names.add(parameter["name"])
    return names


def _body_findings(spec: dict, call: CliCall, operation: dict) -> Iterator[Finding]:
    def finding(kind: str, keys: Iterable[str]) -> Finding:
        return Finding(kind, call.method, call.path, call.location, sorted(keys))

    if not call.body_keys:
        return
    body = operation.get("requestBody")
    if body is None:
        yield finding("BODY-UNEXPECTED", call.body_keys)
        return
    content = body.get("content", {})
    if _JSON_MEDIA not in content:
        return
    fields = _schema_fields(spec, content[_JSON_MEDIA].get("schema", {}))
    if fields is None:
        return
    names, required = fields
    unknown = call.body_keys - names
    if unknown:
        yield finding("BODY-KEY", unknown)
    body_known = not any(text.startswith("json=") for text in call.unresolved)
    missing = required - call.body_keys
    if body_known and missing:
        yield finding("BODY-MISSING", missing)


def find_mismatches(calls: Iterable[CliCall], spec: dict) -> list[Finding]:
    """Compares each CLI call with the operation it calls.

    A call whose method and path the spec lacks is skipped. The path check in
    `audit_endpoints.py` reports it.

    Args:
        calls: The calls from `collect_cli_payloads`.
        spec: The OpenAPI spec of the API.

    Returns:
        The findings, in call order.
    """
    index = _operation_index(spec)
    findings: list[Finding] = []
    for call in calls:
        entry = index.get((call.method, call.path))
        if entry is None:
            continue
        operation, shared = entry
        if operation.get("deprecated"):
            findings.append(Finding("DEPRECATED", call.method, call.path, call.location, []))
        findings.extend(_body_findings(spec, call, operation))
        if call.query_keys:
            unknown = call.query_keys - _query_names(spec, operation, shared)
            if unknown:
                findings.append(
                    Finding("QUERY-KEY", call.method, call.path, call.location, sorted(unknown))
                )
    return findings


def print_report(calls: list[CliCall], findings: list[Finding]) -> None:
    """Prints the findings and the unresolved calls."""
    print(f"## PAYLOAD (body and query keys the route does not read): {len(findings)}")
    for f in findings:
        keys = f" {', '.join(f.keys)}" if f.keys else ""
        print(f"  {f.kind:15s} {f.method:6s} {f.path}{keys}  [{f.location}]")
    print()
    unresolved = [c for c in calls if c.unresolved]
    print(f"## UNRESOLVED (check by hand; never fails --strict): {len(unresolved)}")
    for c in unresolved:
        print(f"  {c.method:6s} {c.path}  {'; '.join(c.unresolved)}  [{c.location}]")
