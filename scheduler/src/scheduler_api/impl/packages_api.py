from __future__ import annotations

from fastapi import HTTPException, status

from scheduler_api.apis.packages_api_base import BasePackagesApi
from scheduler_api.catalog import (
    PackageCatalogError,
    PackageNotFoundError,
    PackageVersionNotFoundError,
    catalog,
)
from scheduler_api.models.get_package200_response import GetPackage200Response
from scheduler_api.models.get_package200_response_manifest import GetPackage200ResponseManifest
from scheduler_api.models.list_packages200_response import ListPackages200Response
from scheduler_api.models.list_packages200_response_items_inner import ListPackages200ResponseItemsInner


class PackagesApiImpl(BasePackagesApi):
    async def list_packages(self) -> ListPackages200Response:
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
    ) -> GetPackage200Response:
        try:
            detail = catalog.get_package_detail(packageName, version)
        except PackageNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except PackageVersionNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except PackageCatalogError as exc:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

        manifest_dict = detail["manifest"].model_dump(by_alias=True, exclude_none=True, mode="json")
        manifest_model = GetPackage200ResponseManifest.from_dict(manifest_dict)

        return GetPackage200Response(
            name=detail["name"],
            version=detail["version"],
            availableVersions=detail.get("availableVersions"),
            manifest=manifest_model,
        )
