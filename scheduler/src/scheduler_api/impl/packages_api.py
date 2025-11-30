from __future__ import annotations

from fastapi import HTTPException, status

from scheduler_api.apis.packages_api_base import BasePackagesApi
from scheduler_api.auth.roles import WORKFLOW_VIEW_ROLES, require_roles
from scheduler_api.catalog import (
    PackageCatalogError,
    PackageNotFoundError,
    PackageVersionNotFoundError,
    catalog,
)
from scheduler_api.models.list_packages200_response import ListPackages200Response
from scheduler_api.models.list_packages200_response_items_inner import ListPackages200ResponseItemsInner
from scheduler_api.models.package_detail import PackageDetail
from scheduler_api.models.package_manifest import PackageManifest


class PackagesApiImpl(BasePackagesApi):
    async def list_packages(self) -> ListPackages200Response:
        require_roles(*WORKFLOW_VIEW_ROLES)
        summaries = catalog.list_packages()
        items = [
            ListPackages200ResponseItemsInner(
                name=summary["name"],
                description=summary.get("description"),
                latestVersion=summary.get("latestVersion"),
                defaultVersion=summary.get("defaultVersion"),
                versions=summary.get("versions", []),
            )
            for summary in summaries
        ]
        return ListPackages200Response(items=items)

    async def get_package(
        self,
        packageName: str,
        version: str | None,
    ) -> PackageDetail:
        require_roles(*WORKFLOW_VIEW_ROLES)
        try:
            detail = catalog.get_package_detail(packageName, version)
        except PackageNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except PackageVersionNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except PackageCatalogError as exc:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

        manifest_dict = detail["manifest"].model_dump(by_alias=True, exclude_none=True, mode="json")
        # Ensure schemas are serialized to plain dicts/bools (avoid BaseModel.schema method leaks)
        nodes = manifest_dict.get("nodes")
        if isinstance(nodes, list):
            cleaned_nodes = []
            for node in nodes:
                if not isinstance(node, dict):
                    continue
                node_copy = dict(node)
                schema_val = node_copy.get("schema")
                if hasattr(schema_val, "model_dump"):
                    node_copy["schema"] = schema_val.model_dump(by_alias=True, exclude_none=True)
                cleaned_nodes.append(node_copy)
            manifest_dict["nodes"] = cleaned_nodes

        manifest_model = PackageManifest.from_dict(manifest_dict)

        return PackageDetail(
            name=detail["name"],
            version=detail["version"],
            availableVersions=detail.get("availableVersions"),
            manifest=manifest_model,
        )
