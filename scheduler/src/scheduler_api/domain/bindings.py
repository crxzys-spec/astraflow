"""Binding and result-delta helpers for the run registry."""

from __future__ import annotations

import copy
from typing import Any, Dict, List, Optional, Tuple

from .models import BindingResolution, BindingScopeHint, WorkflowScopeIndex

_MISSING = object()


def _encode_pointer_segment(segment: str) -> str:
    return str(segment).replace("~", "~0").replace("/", "~1")


def _merge_result_updates(
    target: Dict[str, Any],
    updates: Dict[str, Any],
    path_prefix: str = "",
) -> List[Dict[str, Any]]:
    deltas: List[Dict[str, Any]] = []
    for key, value in updates.items():
        pointer = f"{path_prefix}/{_encode_pointer_segment(key)}" if path_prefix else f"/{_encode_pointer_segment(key)}"
        if value is None:
            if key in target:
                target.pop(key, None)
                deltas.append({"path": pointer, "value": None, "operation": "remove"})
            continue
        if isinstance(value, dict):
            if value:
                existing = target.get(key)
                if isinstance(existing, dict):
                    deltas.extend(_merge_result_updates(existing, value, pointer))
                    continue
                new_value = copy.deepcopy(value)
                if existing != new_value:
                    target[key] = new_value
                    deltas.append({"path": pointer, "value": new_value, "operation": "replace"})
            else:
                if target.get(key) != {}:
                    target[key] = {}
                    deltas.append({"path": pointer, "value": {}, "operation": "replace"})
            continue
        new_value = copy.deepcopy(value) if isinstance(value, (dict, list)) else value
        if target.get(key) != new_value:
            target[key] = new_value
            deltas.append({"path": pointer, "value": new_value, "operation": "replace"})
    return deltas


def _decode_pointer(segment: str) -> str:
    return segment.replace("~1", "/").replace("~0", "~")


def _parse_binding_path(path: Optional[str]) -> Optional[Tuple[str, List[str]]]:
    if not path:
        return None
    segments: List[str]
    if path.startswith("/"):
        segments = [_decode_pointer(part) for part in path.split("/") if part]
    else:
        raw_segments = path.replace("[", ".").replace("]", "").split(".")
        segments = [segment for segment in raw_segments if segment]
    if not segments:
        return None
    root = segments[0]
    if root not in {"parameters", "results"}:
        return None
    return root, segments[1:]


def _parse_scope_prefix(prefix: str) -> Optional[BindingScopeHint]:
    text = prefix.strip()
    if not text:
        return None
    if text.startswith("@"):
        tokens = [token for token in text[1:].split(".") if token]
        node_id = None
        aliases: List[str] = []
        for token in tokens:
            if token.startswith("#"):
                node_id = token[1:] or None
            else:
                aliases.append(token)
        if not aliases:
            return None
        subgraph_aliases: Tuple[str, ...] = tuple(aliases)
        return BindingScopeHint(
            kind="subgraph",
            subgraph_aliases=subgraph_aliases,
            node_id=node_id,
            raw_prefix=text,
        )
    if text.startswith("#"):
        return BindingScopeHint(
            kind="local",
            subgraph_aliases=tuple(),
            node_id=text[1:] or None,
            raw_prefix=text,
        )
    return None


def _scope_hint_from_binding(binding: Any) -> Optional[BindingScopeHint]:
    scope_model = getattr(binding, "scope", None)
    prefix = getattr(binding, "prefix", None)
    if scope_model is not None:
        kind = getattr(scope_model, "kind", None)
        raw_prefix = getattr(scope_model, "prefix", None) or prefix
        subgraph_aliases = list(getattr(scope_model, "subgraph_aliases", []) or [])
        # Back-compat: legacy payloads may still include workflow_alias.
        workflow_alias = getattr(scope_model, "workflow_alias", None)
        if workflow_alias and workflow_alias not in subgraph_aliases:
            subgraph_aliases.insert(0, workflow_alias)
        node_id = getattr(scope_model, "node_id", None)
        return BindingScopeHint(
            kind=kind,
            subgraph_aliases=tuple(subgraph_aliases),
            node_id=node_id,
            raw_prefix=raw_prefix,
        )
    if prefix:
        return _parse_scope_prefix(prefix)
    return None


def _resolve_binding_reference(
    binding: Any,
    owning_node: Optional[str],
    scope_index: Optional[WorkflowScopeIndex],
) -> Optional[BindingResolution]:
    if binding is None:
        return None
    path_value = binding.get("path") if isinstance(binding, dict) else getattr(binding, "path", None)
    parsed = _parse_binding_path(path_value)
    if not parsed or owning_node is None:
        return None
    root, path = parsed
    target_node = owning_node
    if scope_index:
        hint = _scope_hint_from_binding(binding)
        resolved = scope_index.resolve_node(hint, owning_node)
        if not resolved:
            return None
        target_node = resolved
    return BindingResolution(node_id=target_node, root=root, path=path)


def _get_nested_value(container: Optional[Dict[str, Any]], path: List[str]) -> Any:
    current: Any = container
    for key in path:
        if not isinstance(current, dict):
            return _MISSING
        if key not in current:
            return _MISSING
        current = current[key]
    return copy.deepcopy(current)


def _ensure_container(container: Dict[str, Any], key: str) -> Dict[str, Any]:
    value = container.get(key)
    if isinstance(value, dict):
        return value
    new_value: Dict[str, Any] = {}
    container[key] = new_value
    return new_value


def _set_nested_value(container: Dict[str, Any], path: List[str], value: Any) -> None:
    if not path:
        if isinstance(value, dict):
            container.clear()
            container.update(copy.deepcopy(value))
        else:
            raise ValueError("Binding path must not be empty when assigning non-mapping values")
        return
    current = container
    for key in path[:-1]:
        current = _ensure_container(current, key)
    current[path[-1]] = copy.deepcopy(value)
