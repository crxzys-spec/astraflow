# coding: utf-8

from fastapi.testclient import TestClient

import scheduler_api


from pydantic import Field, StrictStr  # noqa: F401
from typing import Optional  # noqa: F401
from typing_extensions import Annotated  # noqa: F401
from scheduler_api.models.auth_login401_response import AuthLogin401Response  # noqa: F401
from scheduler_api.models.clone_workflow_package_request import CloneWorkflowPackageRequest  # noqa: F401
from scheduler_api.models.get_workflow_package200_response import GetWorkflowPackage200Response  # noqa: F401
from scheduler_api.models.list_workflow_package_versions200_response import ListWorkflowPackageVersions200Response  # noqa: F401
from scheduler_api.models.list_workflow_packages200_response import ListWorkflowPackages200Response  # noqa: F401
from scheduler_api.models.persist_workflow201_response import PersistWorkflow201Response  # noqa: F401
from scheduler_api.models.publish_workflow200_response import PublishWorkflow200Response  # noqa: F401
from scheduler_api.models.publish_workflow_request import PublishWorkflowRequest  # noqa: F401


def test_list_workflow_packages(client: TestClient):
    """Test case for list_workflow_packages

    List published workflow packages
    """
    params = [("limit", 50),     ("cursor", 'cursor_example'),     ("owner", 'owner_example'),     ("visibility", 'visibility_example'),     ("search", 'search_example')]
    headers = {
        "Authorization": "Bearer special-key",
    }
    # uncomment below to make a request
    #response = client.request(
    #    "GET",
    #    "/api/v1/workflow-packages",
    #    headers=headers,
    #    params=params,
    #)

    # uncomment below to assert the status code of the HTTP response
    #assert response.status_code == 200


def test_get_workflow_package(client: TestClient):
    """Test case for get_workflow_package

    Get a workflow package detail
    """

    headers = {
        "Authorization": "Bearer special-key",
    }
    # uncomment below to make a request
    #response = client.request(
    #    "GET",
    #    "/api/v1/workflow-packages/{packageId}".format(packageId='package_id_example'),
    #    headers=headers,
    #)

    # uncomment below to assert the status code of the HTTP response
    #assert response.status_code == 200


def test_list_workflow_package_versions(client: TestClient):
    """Test case for list_workflow_package_versions

    List versions for a workflow package
    """

    headers = {
        "Authorization": "Bearer special-key",
    }
    # uncomment below to make a request
    #response = client.request(
    #    "GET",
    #    "/api/v1/workflow-packages/{packageId}/versions".format(packageId='package_id_example'),
    #    headers=headers,
    #)

    # uncomment below to assert the status code of the HTTP response
    #assert response.status_code == 200


def test_clone_workflow_package(client: TestClient):
    """Test case for clone_workflow_package

    Clone a workflow package version into the caller's workspace
    """
    clone_workflow_package_request = scheduler_api.CloneWorkflowPackageRequest()

    headers = {
        "Authorization": "Bearer special-key",
    }
    # uncomment below to make a request
    #response = client.request(
    #    "POST",
    #    "/api/v1/workflow-packages/{packageId}/clone".format(packageId='package_id_example'),
    #    headers=headers,
    #    json=clone_workflow_package_request,
    #)

    # uncomment below to assert the status code of the HTTP response
    #assert response.status_code == 200


def test_publish_workflow(client: TestClient):
    """Test case for publish_workflow

    Publish a workflow draft to the Store
    """
    publish_workflow_request = scheduler_api.PublishWorkflowRequest(version="1.0.0")

    headers = {
        "Authorization": "Bearer special-key",
    }
    # uncomment below to make a request
    #response = client.request(
    #    "POST",
    #    "/api/v1/workflows/{workflowId}/publish".format(workflowId='workflow_id_example'),
    #    headers=headers,
    #    json=publish_workflow_request,
    #)

    # uncomment below to assert the status code of the HTTP response
    #assert response.status_code == 200
