# coding: utf-8

from fastapi.testclient import TestClient


from typing import Any  # noqa: F401
from scheduler_api.models.error import Error  # noqa: F401
from scheduler_api.models.registry_account_link import RegistryAccountLink  # noqa: F401
from scheduler_api.models.registry_account_link_request import RegistryAccountLinkRequest  # noqa: F401
from scheduler_api.models.registry_workflow_import_request import RegistryWorkflowImportRequest  # noqa: F401
from scheduler_api.models.registry_workflow_import_response import RegistryWorkflowImportResponse  # noqa: F401


def test_get_registry_account(client: TestClient):
    """Test case for get_registry_account

    Get linked registry account
    """

    headers = {
        "Authorization": "Bearer special-key",
    }
    # uncomment below to make a request
    #response = client.request(
    #    "GET",
    #    "/api/v1/registry/account",
    #    headers=headers,
    #)

    # uncomment below to assert the status code of the HTTP response
    #assert response.status_code == 200


def test_link_registry_account(client: TestClient):
    """Test case for link_registry_account

    Link registry account
    """
    registry_account_link_request = {"registry_user_id":"registryUserId","registry_username":"registryUsername"}

    headers = {
        "Authorization": "Bearer special-key",
    }
    # uncomment below to make a request
    #response = client.request(
    #    "POST",
    #    "/api/v1/registry/account",
    #    headers=headers,
    #    json=registry_account_link_request,
    #)

    # uncomment below to assert the status code of the HTTP response
    #assert response.status_code == 200


def test_unlink_registry_account(client: TestClient):
    """Test case for unlink_registry_account

    Unlink registry account
    """

    headers = {
        "Authorization": "Bearer special-key",
    }
    # uncomment below to make a request
    #response = client.request(
    #    "DELETE",
    #    "/api/v1/registry/account",
    #    headers=headers,
    #)

    # uncomment below to assert the status code of the HTTP response
    #assert response.status_code == 200


def test_import_registry_workflow(client: TestClient):
    """Test case for import_registry_workflow

    Import a registry workflow into the platform
    """
    registry_workflow_import_request = {"version_id":"versionId","package_id":"packageId","name":"name","version":"version"}

    headers = {
        "Authorization": "Bearer special-key",
    }
    # uncomment below to make a request
    #response = client.request(
    #    "POST",
    #    "/api/v1/registry/workflows/import",
    #    headers=headers,
    #    json=registry_workflow_import_request,
    #)

    # uncomment below to assert the status code of the HTTP response
    #assert response.status_code == 200

