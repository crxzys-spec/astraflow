"""Helpers for extracting workflow package dependencies."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WorkflowPackageDependency:
    name: str
    version: str

    def to_dict(self) -> dict[str, str]:
        return {"name": self.name, "version": self.version}


def extract_package_dependencies(definition: dict[str, object]) -> list[WorkflowPackageDependency]:
    nodes = definition.get("nodes")
    if not isinstance(nodes, list):
        return []
    seen: set[tuple[str, str]] = set()
    deps: list[WorkflowPackageDependency] = []
    for node in nodes:
        if not isinstance(node, dict):
            continue
        package = node.get("package")
        if not isinstance(package, dict):
            continue
        name = package.get("name")
        version = package.get("version")
        if not isinstance(name, str) or not isinstance(version, str):
            continue
        key = (name, version)
        if key in seen:
            continue
        seen.add(key)
        deps.append(WorkflowPackageDependency(name=name, version=version))
    return deps
