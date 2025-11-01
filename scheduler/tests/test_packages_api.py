# coding: utf-8

from fastapi.testclient import TestClient


from pydantic import Field, StrictStr  # noqa: F401
from typing import Optional  # noqa: F401
from typing_extensions import Annotated  # noqa: F401
from scheduler_api.models.get_package200_response import GetPackage200Response  # noqa: F401
from scheduler_api.models.list_packages200_response import ListPackages200Response  # noqa: F401
from scheduler_api.models.start_run400_response import StartRun400Response  # noqa: F401


def test_list_packages(client: TestClient):
    """Test case for list_packages

    List available packages
    """

    headers = {
        "Authorization": "Bearer special-key",
    }
    # uncomment below to make a request
    #response = client.request(
    #    "GET",
    #    "/api/v1/packages",
    #    headers=headers,
    #)

    # uncomment below to assert the status code of the HTTP response
    #assert response.status_code == 200


def test_get_package(client: TestClient):
    """Test case for get_package

    Get package detail
    """
    params = [("version", 'version_example')]
    headers = {
        "Authorization": "Bearer special-key",
    }
    # uncomment below to make a request
    #response = client.request(
    #    "GET",
    #    "/api/v1/packages/{packageName}".format(packageName='package_name_example'),
    #    headers=headers,
    #    params=params,
    #)

    # uncomment below to assert the status code of the HTTP response
    #assert response.status_code == 200

