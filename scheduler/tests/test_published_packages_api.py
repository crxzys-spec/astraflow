# coding: utf-8

from fastapi.testclient import TestClient


from pydantic import Field, StrictBytes, StrictStr  # noqa: F401
from typing import Optional, Tuple, Union  # noqa: F401
from typing_extensions import Annotated  # noqa: F401
from scheduler_api.models.error import Error  # noqa: F401
from scheduler_api.models.package_detail import PackageDetail  # noqa: F401
from scheduler_api.models.package_list import PackageList  # noqa: F401


def test_list_published_packages(client: TestClient):
    """Test case for list_published_packages

    List published packages
    """

    headers = {
        "Authorization": "Bearer special-key",
    }
    # uncomment below to make a request
    #response = client.request(
    #    "GET",
    #    "/api/v1/published-packages",
    #    headers=headers,
    #)

    # uncomment below to assert the status code of the HTTP response
    #assert response.status_code == 200


def test_upload_published_package(client: TestClient):
    """Test case for upload_published_package

    Upload a published package archive
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
    #    "/api/v1/published-packages",
    #    headers=headers,
    #    data=data,
    #)

    # uncomment below to assert the status code of the HTTP response
    #assert response.status_code == 200


def test_get_published_package(client: TestClient):
    """Test case for get_published_package

    Get published package detail
    """
    params = [("version", 'version_example')]
    headers = {
        "Authorization": "Bearer special-key",
    }
    # uncomment below to make a request
    #response = client.request(
    #    "GET",
    #    "/api/v1/published-packages/{packageName}".format(packageName='package_name_example'),
    #    headers=headers,
    #    params=params,
    #)

    # uncomment below to assert the status code of the HTTP response
    #assert response.status_code == 200


def test_download_published_package(client: TestClient):
    """Test case for download_published_package

    Download published package archive
    """
    params = [("version", 'version_example')]
    headers = {
        "Authorization": "Bearer special-key",
    }
    # uncomment below to make a request
    #response = client.request(
    #    "GET",
    #    "/api/v1/published-packages/{packageName}/archive".format(packageName='package_name_example'),
    #    headers=headers,
    #    params=params,
    #)

    # uncomment below to assert the status code of the HTTP response
    #assert response.status_code == 200

