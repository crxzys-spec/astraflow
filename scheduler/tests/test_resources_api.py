# coding: utf-8

from fastapi.testclient import TestClient


from pydantic import StrictBytes, StrictStr  # noqa: F401
from typing import Any, Tuple, Union  # noqa: F401
from scheduler_api.models.error import Error  # noqa: F401
from scheduler_api.models.resource import Resource  # noqa: F401


def test_upload_resource(client: TestClient):
    """Test case for upload_resource

    Upload resource
    """

    headers = {
        "Authorization": "Bearer special-key",
    }
    data = {
        "file": '/path/to/file'
    }
    # uncomment below to make a request
    #response = client.request(
    #    "POST",
    #    "/api/v1/resources",
    #    headers=headers,
    #    data=data,
    #)

    # uncomment below to assert the status code of the HTTP response
    #assert response.status_code == 200


def test_get_resource(client: TestClient):
    """Test case for get_resource

    Get resource metadata
    """

    headers = {
        "Authorization": "Bearer special-key",
    }
    # uncomment below to make a request
    #response = client.request(
    #    "GET",
    #    "/api/v1/resources/{resourceId}".format(resourceId='resource_id_example'),
    #    headers=headers,
    #)

    # uncomment below to assert the status code of the HTTP response
    #assert response.status_code == 200


def test_delete_resource(client: TestClient):
    """Test case for delete_resource

    Delete resource
    """

    headers = {
        "Authorization": "Bearer special-key",
    }
    # uncomment below to make a request
    #response = client.request(
    #    "DELETE",
    #    "/api/v1/resources/{resourceId}".format(resourceId='resource_id_example'),
    #    headers=headers,
    #)

    # uncomment below to assert the status code of the HTTP response
    #assert response.status_code == 200


def test_download_resource(client: TestClient):
    """Test case for download_resource

    Download resource
    """

    headers = {
        "Authorization": "Bearer special-key",
    }
    # uncomment below to make a request
    #response = client.request(
    #    "GET",
    #    "/api/v1/resources/{resourceId}/download".format(resourceId='resource_id_example'),
    #    headers=headers,
    #)

    # uncomment below to assert the status code of the HTTP response
    #assert response.status_code == 200

