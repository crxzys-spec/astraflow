# coding: utf-8

from fastapi.testclient import TestClient


from pydantic import Field, StrictStr  # noqa: F401
from typing import Any, Optional  # noqa: F401
from typing_extensions import Annotated  # noqa: F401
from hub_api.models.hub_package_detail import HubPackageDetail  # noqa: F401
from hub_api.models.package_list_response import PackageListResponse  # noqa: F401


def test_list_packages(client: TestClient):
    """Test case for list_packages

    List packages
    """
    params = [("q", 'q_example'),     ("tag", 'tag_example'),     ("owner", 'owner_example'),     ("page", 1),     ("page_size", 20)]
    headers = {
    }
    # uncomment below to make a request
    #response = client.request(
    #    "GET",
    #    "/api/v1/packages",
    #    headers=headers,
    #    params=params,
    #)

    # uncomment below to assert the status code of the HTTP response
    #assert response.status_code == 200


def test_get_package(client: TestClient):
    """Test case for get_package

    Get package detail
    """

    headers = {
    }
    # uncomment below to make a request
    #response = client.request(
    #    "GET",
    #    "/api/v1/packages/{name}".format(name='name_example'),
    #    headers=headers,
    #)

    # uncomment below to assert the status code of the HTTP response
    #assert response.status_code == 200

