from __future__ import annotations

from scheduler_api.http.errors import bad_request, forbidden, not_found
from pydantic import StrictStr

from scheduler_api.apis.package_vault_api_base import BasePackageVaultApi
from scheduler_api.auth.roles import WORKFLOW_EDIT_ROLES, WORKFLOW_VIEW_ROLES, require_roles
from scheduler_api.models.package_vault_item import PackageVaultItem
from scheduler_api.models.package_vault_list import PackageVaultList
from scheduler_api.models.package_vault_upsert_request import PackageVaultUpsertRequest
from scheduler_api.domain.resources import StoredPackageVaultItem
from scheduler_api.service.facade import resource_services


class PackageVaultApiImpl(BasePackageVaultApi):
    async def list_package_vault(self, package_name: StrictStr) -> PackageVaultList:
        token = require_roles(*WORKFLOW_VIEW_ROLES)
        if not token or not token.sub:
            raise forbidden("Authentication required.")
        items = resource_services.package_vault.list(owner_id=token.sub, package_name=str(package_name))
        return PackageVaultList(items=[_to_vault_model(item) for item in items])

    async def upsert_package_vault(
        self,
        package_vault_upsert_request: PackageVaultUpsertRequest,
    ) -> PackageVaultList:
        token = require_roles(*WORKFLOW_EDIT_ROLES)
        if package_vault_upsert_request is None:
            raise bad_request("Missing vault payload.")
        payload = package_vault_upsert_request.model_dump(by_alias=True, exclude_none=True)
        package_name = payload.get("packageName") or package_vault_upsert_request.package_name
        items = payload.get("items") or package_vault_upsert_request.items
        if not package_name or not items:
            raise bad_request("Missing vault items.")
        entries: list[tuple[str, str]] = []
        for item in items:
            key = getattr(item, "key", None) if not isinstance(item, dict) else item.get("key")
            value = getattr(item, "value", None) if not isinstance(item, dict) else item.get("value")
            key = str(key).strip() if key is not None else ""
            if not key:
                continue
            entries.append((key, "" if value is None else str(value)))
        if not entries:
            raise bad_request("Missing vault items.")
        stored_items = resource_services.package_vault.upsert_items(
            owner_id=token.sub,
            package_name=str(package_name),
            items=entries,
        )
        return PackageVaultList(items=[_to_vault_model(item) for item in stored_items])

    async def delete_package_vault_item(self, packageName: StrictStr, key: StrictStr) -> None:
        token = require_roles(*WORKFLOW_EDIT_ROLES)
        existing = resource_services.package_vault.get_value(
            owner_id=token.sub if token else "",
            package_name=str(packageName),
            key=str(key),
        )
        if existing is None:
            raise not_found("Vault entry not found.")
        resource_services.package_vault.delete(
            owner_id=token.sub if token else "",
            package_name=str(packageName),
            key=str(key),
        )
        return None


def _to_vault_model(item: StoredPackageVaultItem) -> PackageVaultItem:
    return PackageVaultItem(
        item_id=item.item_id,
        owner_id=item.owner_id,
        package_name=item.package_name,
        key=item.key,
        value=item.value,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )
