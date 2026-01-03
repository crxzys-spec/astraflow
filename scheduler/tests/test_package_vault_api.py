# coding: utf-8

from fastapi.testclient import TestClient


from pydantic import StrictStr  # noqa: F401
from typing import Any  # noqa: F401
from scheduler_api.models.error import Error  # noqa: F401
from scheduler_api.models.package_vault_list import PackageVaultList  # noqa: F401
from scheduler_api.models.package_vault_upsert_request import PackageVaultUpsertRequest  # noqa: F401


def test_list_package_vault(client: TestClient):
    """Test case for list_package_vault

    List package vault entries
    """
    params = [("package_name", 'package_name_example')]
    headers = {
        "Authorization": "Bearer special-key",
    }
    # uncomment below to make a request
    #response = client.request(
    #    "GET",
    #    "/api/v1/package-vault",
    #    headers=headers,
    #    params=params,
    #)

    # uncomment below to assert the status code of the HTTP response
    #assert response.status_code == 200


def test_upsert_package_vault(client: TestClient):
    """Test case for upsert_package_vault

    Upsert package vault entries
    """
    package_vault_upsert_request = {"package_name":"packageName","items":[{"value":"value","key":"key"},{"value":"value","key":"key"}]}

    headers = {
        "Authorization": "Bearer special-key",
    }
    # uncomment below to make a request
    #response = client.request(
    #    "PUT",
    #    "/api/v1/package-vault",
    #    headers=headers,
    #    json=package_vault_upsert_request,
    #)

    # uncomment below to assert the status code of the HTTP response
    #assert response.status_code == 200


def test_delete_package_vault_item(client: TestClient):
    """Test case for delete_package_vault_item

    Delete package vault entry
    """

    headers = {
        "Authorization": "Bearer special-key",
    }
    # uncomment below to make a request
    #response = client.request(
    #    "DELETE",
    #    "/api/v1/package-vault/{packageName}/{key}".format(packageName='package_name_example', key='key_example'),
    #    headers=headers,
    #)

    # uncomment below to assert the status code of the HTTP response
    #assert response.status_code == 200

