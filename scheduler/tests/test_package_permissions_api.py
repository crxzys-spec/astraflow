# coding: utf-8

from fastapi.testclient import TestClient


from pydantic import StrictStr  # noqa: F401
from typing import Any, Optional  # noqa: F401
from scheduler_api.models.error import Error  # noqa: F401
from scheduler_api.models.package_permission import PackagePermission  # noqa: F401
from scheduler_api.models.package_permission_create_request import PackagePermissionCreateRequest  # noqa: F401
from scheduler_api.models.package_permission_list import PackagePermissionList  # noqa: F401


def test_list_package_permissions(client: TestClient):
    """Test case for list_package_permissions

    List package permissions
    """
    params = [("package_name", 'package_name_example')]
    headers = {
        "Authorization": "Bearer special-key",
    }
    # uncomment below to make a request
    #response = client.request(
    #    "GET",
    #    "/api/v1/package-permissions",
    #    headers=headers,
    #    params=params,
    #)

    # uncomment below to assert the status code of the HTTP response
    #assert response.status_code == 200


def test_create_package_permission(client: TestClient):
    """Test case for create_package_permission

    Grant package permissions
    """
    package_permission_create_request = {"types":["types","types"],"permission_key":"permissionKey","package_name":"packageName","actions":["actions","actions"],"providers":["providers","providers"]}

    headers = {
        "Authorization": "Bearer special-key",
    }
    # uncomment below to make a request
    #response = client.request(
    #    "POST",
    #    "/api/v1/package-permissions",
    #    headers=headers,
    #    json=package_permission_create_request,
    #)

    # uncomment below to assert the status code of the HTTP response
    #assert response.status_code == 200


def test_delete_package_permission(client: TestClient):
    """Test case for delete_package_permission

    Revoke package permission
    """

    headers = {
        "Authorization": "Bearer special-key",
    }
    # uncomment below to make a request
    #response = client.request(
    #    "DELETE",
    #    "/api/v1/package-permissions/{permissionId}".format(permissionId='permission_id_example'),
    #    headers=headers,
    #)

    # uncomment below to assert the status code of the HTTP response
    #assert response.status_code == 200

