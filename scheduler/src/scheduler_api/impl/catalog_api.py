# coding: utf-8

from __future__ import annotations

from typing import List, Optional

from scheduler_api.apis.catalog_api_base import BaseCatalogApi
from scheduler_api.catalog import catalog
from scheduler_api.catalog.package_catalog import _version_key
from scheduler_api.control_plane.network import worker_gateway
from scheduler_api.models.catalog_node import CatalogNode
from scheduler_api.models.catalog_node_search_response import CatalogNodeSearchResponse
from scheduler_api.models.catalog_node_version import CatalogNodeVersion
from scheduler_api.models.manifest_json_schema import ManifestJsonSchema
from scheduler_api.models.manifest_node import ManifestNode
from scheduler_api.models.manifest_node_schema import ManifestNodeSchema
from scheduler_api.models.manifest_node_ui import ManifestNodeUI


def _coerce_status(status_obj, default: str = "draft") -> str:
    """Normalize status enums/strings to the accepted ManifestNode values."""
    value = getattr(status_obj, "value", status_obj)
    if isinstance(value, str):
        value = value.lower()
    if value in ("draft", "published", "deprecated"):
        return value
    return default


def _convert_manifest_node(node) -> ManifestNode | None:
    """Convert a shared manifest Node into the public ManifestNode shape."""
    def _make_json_schema(payload):
        if payload is None:
            return None
        try:
            return ManifestJsonSchema(payload)
        except Exception:
            try:
                if hasattr(payload, "model_dump"):
                    return ManifestJsonSchema(payload.model_dump())
            except Exception:
                return None
        return None

    try:
        schema_payload = getattr(node, "schema_", None)
        if schema_payload is not None and hasattr(schema_payload, "root"):
            schema_payload = schema_payload.root
        parameters_payload = None
        results_payload = None
        if isinstance(schema_payload, dict):
            parameters_payload = schema_payload.get("parameters")
            results_payload = schema_payload.get("results")
        schema_model = ManifestNodeSchema(
            parameters=_make_json_schema(parameters_payload),
            results=_make_json_schema(results_payload),
        )
        if schema_model.parameters is None and schema_model.results is None:
            schema_model = ManifestNodeSchema()
        ui_payload = getattr(node, "ui", None)
        ui_model = None
        if ui_payload is not None and hasattr(ui_payload, "model_dump"):
            ui_model = ManifestNodeUI.from_dict(ui_payload.model_dump(by_alias=True))
        elif ui_payload is not None and isinstance(ui_payload, dict):
            ui_model = ManifestNodeUI.from_dict(ui_payload)
        return ManifestNode(
            type=node.type,
            role=getattr(node, "role", None),
            status=_coerce_status(getattr(node, "status", "")),
            category=node.category,
            label=node.label or node.type,
            description=getattr(node, "description", None),
            tags=getattr(node, "tags", None),
            adapter=node.adapter,
            handler=node.handler,
            config=getattr(node, "config", None),
            schema=schema_model,
            ui=ui_model,
        )
    except Exception:
        pass

    try:
        return ManifestNode.model_validate(node.model_dump(by_alias=True))
    except Exception:
        try:
            return ManifestNode(
                type=getattr(node, "type", "unknown"),
                role=getattr(node, "role", None),
                status=_coerce_status(getattr(node, "status", "draft") or "draft"),
                category=getattr(node, "category", "default"),
                label=getattr(node, "label", getattr(node, "type", "unknown")),
                description=getattr(node, "description", None),
                tags=getattr(node, "tags", None),
                adapter=getattr(node, "adapter", "placeholder"),
                handler=getattr(node, "handler", "handler"),
                config=getattr(node, "config", None),
                schema=ManifestNodeSchema(),
                ui=None,
            )
        except Exception:
            return None


def _build_catalog_nodes() -> List[CatalogNode]:
    """Aggregate nodes across system manifests + worker-reported manifests."""

    manifest_entries: list[tuple[str, str, dict]] = []

    # System/local manifests from PackageCatalog (system nodes live here).
    try:
        summaries = catalog.list_packages()
        for summary in summaries:
            name = summary.get("name")
            versions = summary.get("versions") or []
            for version in versions:
                try:
                    manifest_model = catalog.get_manifest(name, version)
                    manifest = (
                        manifest_model.model_dump(by_alias=True)
                        if hasattr(manifest_model, "model_dump")
                        else manifest_model
                    )
                except Exception:
                    continue
                manifest_entries.append((name, version, manifest))
    except Exception:
        pass

    # Worker-reported manifests (hot data).
    try:
        for session in worker_gateway.list_sessions().values():
            for m in session.manifests or []:
                try:
                    name = getattr(m, "name", None) or m.get("name")  # type: ignore[attr-defined]
                    version = getattr(m, "version", None) or m.get("version")  # type: ignore[attr-defined]
                    manifest = getattr(m, "manifest", None) or m.get("manifest")  # type: ignore[attr-defined]
                except Exception:
                    continue
                if not name or not version or not manifest:
                    continue
                manifest_entries.append((str(name), str(version), manifest))
    except Exception:
        pass

    # Group manifests per package to derive defaults.
    grouped: dict[str, list[tuple[str, dict]]] = {}
    for name, version, manifest in manifest_entries:
        grouped.setdefault(name, []).append((version, manifest))

    aggregated: dict[tuple[str, str], CatalogNode] = {}
    version_index: dict[tuple[str, str], dict[str, CatalogNodeVersion]] = {}

    for name, versions_manifests in grouped.items():
        versions = sorted({ver for ver, _ in versions_manifests}, key=_version_key, reverse=True)
        default_version = versions[0] if versions else None
        latest_version = versions[0] if versions else None
        for version, manifest in versions_manifests:
            nodes_payload = manifest.get("nodes") if isinstance(manifest, dict) else None
            if not nodes_payload:
                continue
            for node_payload in nodes_payload:
                if hasattr(node_payload, "model_dump"):
                    node_dict = node_payload.model_dump(by_alias=True)
                elif isinstance(node_payload, dict):
                    node_dict = node_payload
                else:
                    continue
                node_type = node_dict.get("type")
                if not node_type:
                    continue
                key = (name, node_type)
                entry = aggregated.get(key)
                if not entry:
                    entry = CatalogNode(
                        type=node_type,
                        label=node_dict.get("label") or node_type,
                        category=node_dict.get("category"),
                        role=node_dict.get("role"),
                        description=node_dict.get("description"),
                        tags=node_dict.get("tags"),
                        status=_coerce_status(node_dict.get("status", "") or ""),
                        packageName=name,
                        defaultVersion=default_version,
                        latestVersion=latest_version,
                        versions=[],
                    )
                    aggregated[key] = entry
                    version_index[key] = {}
                template = None
                try:
                    template = ManifestNode.model_validate(node_dict)
                except Exception:
                    template = _convert_manifest_node(node_payload)
                if template is None:
                    template = ManifestNode(
                        type=node_type,
                        role=node_dict.get("role"),
                        status=_coerce_status(node_dict.get("status", "draft") or "draft"),
                        category=node_dict.get("category", "default"),
                        label=node_dict.get("label") or node_type,
                        description=node_dict.get("description"),
                        tags=node_dict.get("tags"),
                        adapter=node_dict.get("adapter", "placeholder"),
                        handler=node_dict.get("handler", "handler"),
                        config=node_dict.get("config"),
                        schema=ManifestNodeSchema(),
                        ui=None,
                    )
                # de-duplicate per version, prefer non-placeholder templates
                versions_map = version_index[key]
                existing = versions_map.get(version)

                def is_placeholder(t: ManifestNode | None) -> bool:
                    if not t:
                        return True
                    return (
                        t.type == "unknown"
                        or t.label == "unknown"
                        or t.adapter == "placeholder"
                    )

                should_replace = existing is None or (
                    is_placeholder(existing.template) and not is_placeholder(template)
                )
                if should_replace:
                    versions_map[version] = CatalogNodeVersion(
                        version=version,
                        status=_coerce_status(node_dict.get("status") or None),
                        template=template,
                    )

    # attach merged versions back to catalog nodes
    for key, entry in aggregated.items():
        versions_map = version_index.get(key, {})
        # Drop placeholder templates when we have a real template for the same version.
        def is_placeholder_version(v: CatalogNodeVersion) -> bool:
            t = v.template
            return (
                t is None
                or t.type == "unknown"
                or t.label == "unknown"
                or t.adapter == "placeholder"
            )

        # Prefer non-placeholder versions; if none exist, keep whatever we have so the node
        # remains discoverable (even if minimal).
        real_versions = {ver: v for ver, v in versions_map.items() if not is_placeholder_version(v)}
        selected_versions = real_versions if real_versions else versions_map

        entry.versions = sorted(selected_versions.values(), key=lambda v: _version_key(v.version))

    return sorted(aggregated.values(), key=lambda item: (item.package_name, item.label))


class CatalogApiImpl(BaseCatalogApi):
    async def search_catalog_nodes(
        self,
        q: str,
        package: Optional[str],
    ) -> CatalogNodeSearchResponse:
        nodes = _build_catalog_nodes()
        query = (q or "").strip()
        query_lower = "" if query in ("", "*") else query.lower()

        def matches(node: CatalogNode) -> bool:
            if package and node.package_name != package:
                return False
            if not query_lower:
                return True
            haystack = " ".join(
                str(part)
                for part in [
                    node.label,
                    node.type,
                    node.description or "",
                    " ".join(node.tags or []),
                ]
            ).lower()
            return query_lower in haystack

        filtered = [node for node in nodes if matches(node)]
        return CatalogNodeSearchResponse(items=filtered)
