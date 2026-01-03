# coding: utf-8

from fastapi.testclient import TestClient


from pydantic import Field, StrictBytes, StrictStr  # noqa: F401
from typing import List, Optional, Tuple, Union  # noqa: F401
from typing_extensions import Annotated  # noqa: F401
from scheduler_api.models.error import Error  # noqa: F401
from scheduler_api.models.hub_package_detail import HubPackageDetail  # noqa: F401
from scheduler_api.models.hub_package_install_request import HubPackageInstallRequest  # noqa: F401
from scheduler_api.models.hub_package_install_response import HubPackageInstallResponse  # noqa: F401
from scheduler_api.models.hub_package_list_response import HubPackageListResponse  # noqa: F401
from scheduler_api.models.hub_package_version_detail import HubPackageVersionDetail  # noqa: F401
from scheduler_api.models.hub_visibility import HubVisibility  # noqa: F401


def test_list_hub_packages(client: TestClient):
    """Test case for list_hub_packages

    List hub packages
    """
    params = [("q", 'q_example'),     ("tag", 'tag_example'),     ("owner", 'owner_example'),     ("page", 1),     ("page_size", 20)]
    headers = {
        "Authorization": "Bearer special-key",
    }
    # uncomment below to make a request
    #response = client.request(
    #    "GET",
    #    "/api/v1/hub/packages",
    #    headers=headers,
    #    params=params,
    #)

    # uncomment below to assert the status code of the HTTP response
    #assert response.status_code == 200


def test_publish_hub_package(client: TestClient):
    """Test case for publish_hub_package

    Publish a package archive to Hub
    """

    headers = {
        "Authorization": "Bearer special-key",
    }
    data = {
        "file": '/path/to/file',
        "visibility": scheduler_api.HubVisibility(),
        "summary": 'summary_example',
        "readme": 'readme_example',
        "tags": ['tags_example']
    }
    # uncomment below to make a request
    #response = client.request(
    #    "POST",
    #    "/api/v1/hub/packages",
    #    headers=headers,
    #    data=data,
    #)

    # uncomment below to assert the status code of the HTTP response
    #assert response.status_code == 200


def test_get_hub_package(client: TestClient):
    """Test case for get_hub_package

    Get hub package detail
    """

    headers = {
        "Authorization": "Bearer special-key",
    }
    # uncomment below to make a request
    #response = client.request(
    #    "GET",
    #    "/api/v1/hub/packages/{packageName}".format(packageName='package_name_example'),
    #    headers=headers,
    #)

    # uncomment below to assert the status code of the HTTP response
    #assert response.status_code == 200


def test_get_hub_package_version(client: TestClient):
    """Test case for get_hub_package_version

    Get hub package version detail
    """

    headers = {
        "Authorization": "Bearer special-key",
    }
    # uncomment below to make a request
    #response = client.request(
    #    "GET",
    #    "/api/v1/hub/packages/{packageName}/versions/{version}".format(packageName='package_name_example', version='version_example'),
    #    headers=headers,
    #)

    # uncomment below to assert the status code of the HTTP response
    #assert response.status_code == 200


def test_download_hub_package_archive(client: TestClient):
    """Test case for download_hub_package_archive

    Download hub package archive
    """
    params = [("version", 'version_example')]
    headers = {
        "Authorization": "Bearer special-key",
    }
    # uncomment below to make a request
    #response = client.request(
    #    "GET",
    #    "/api/v1/hub/packages/{packageName}/archive".format(packageName='package_name_example'),
    #    headers=headers,
    #    params=params,
    #)

    # uncomment below to assert the status code of the HTTP response
    #assert response.status_code == 200


def test_install_hub_package(client: TestClient):
    """Test case for install_hub_package

    Install hub package into the local catalog
    """
    hub_package_install_request = {"version":"version"}

    headers = {
        "Authorization": "Bearer special-key",
    }
    # uncomment below to make a request
    #response = client.request(
    #    "POST",
    #    "/api/v1/hub/packages/{packageName}/install".format(packageName='package_name_example'),
    #    headers=headers,
    #    json=hub_package_install_request,
    #)

    # uncomment below to assert the status code of the HTTP response
    #assert response.status_code == 200

