# coding: utf-8

from fastapi.testclient import TestClient


from pydantic import Field, StrictStr  # noqa: F401
from typing import Any, Dict, Optional  # noqa: F401
from typing_extensions import Annotated  # noqa: F401
from scheduler_api.models.error import Error  # noqa: F401
from scheduler_api.models.hub_workflow_detail import HubWorkflowDetail  # noqa: F401
from scheduler_api.models.hub_workflow_import_request import HubWorkflowImportRequest  # noqa: F401
from scheduler_api.models.hub_workflow_import_response import HubWorkflowImportResponse  # noqa: F401
from scheduler_api.models.hub_workflow_list_response import HubWorkflowListResponse  # noqa: F401
from scheduler_api.models.hub_workflow_publish_request import HubWorkflowPublishRequest  # noqa: F401
from scheduler_api.models.hub_workflow_publish_response import HubWorkflowPublishResponse  # noqa: F401
from scheduler_api.models.hub_workflow_version_detail import HubWorkflowVersionDetail  # noqa: F401
from scheduler_api.models.hub_workflow_version_list import HubWorkflowVersionList  # noqa: F401


def test_list_hub_workflows(client: TestClient):
    """Test case for list_hub_workflows

    List hub workflows
    """
    params = [("q", 'q_example'),     ("tag", 'tag_example'),     ("owner", 'owner_example'),     ("page", 1),     ("page_size", 20)]
    headers = {
        "Authorization": "Bearer special-key",
    }
    # uncomment below to make a request
    #response = client.request(
    #    "GET",
    #    "/api/v1/hub/workflows",
    #    headers=headers,
    #    params=params,
    #)

    # uncomment below to assert the status code of the HTTP response
    #assert response.status_code == 200


def test_publish_hub_workflow(client: TestClient):
    """Test case for publish_hub_workflow

    Publish a workflow to Hub
    """
    hub_workflow_publish_request = {"summary":"summary","visibility":"private","name":"name","description":"description","definition":{"key":""},"version":"version","workflow_id":"workflowId","preview_image":"previewImage","tags":["tags","tags"],"dependencies":[{"name":"name","version":"version"},{"name":"name","version":"version"}]}

    headers = {
        "Authorization": "Bearer special-key",
    }
    # uncomment below to make a request
    #response = client.request(
    #    "POST",
    #    "/api/v1/hub/workflows",
    #    headers=headers,
    #    json=hub_workflow_publish_request,
    #)

    # uncomment below to assert the status code of the HTTP response
    #assert response.status_code == 200


def test_get_hub_workflow(client: TestClient):
    """Test case for get_hub_workflow

    Get hub workflow detail
    """

    headers = {
        "Authorization": "Bearer special-key",
    }
    # uncomment below to make a request
    #response = client.request(
    #    "GET",
    #    "/api/v1/hub/workflows/{workflowId}".format(workflowId='workflow_id_example'),
    #    headers=headers,
    #)

    # uncomment below to assert the status code of the HTTP response
    #assert response.status_code == 200


def test_list_hub_workflow_versions(client: TestClient):
    """Test case for list_hub_workflow_versions

    List hub workflow versions
    """

    headers = {
        "Authorization": "Bearer special-key",
    }
    # uncomment below to make a request
    #response = client.request(
    #    "GET",
    #    "/api/v1/hub/workflows/{workflowId}/versions".format(workflowId='workflow_id_example'),
    #    headers=headers,
    #)

    # uncomment below to assert the status code of the HTTP response
    #assert response.status_code == 200


def test_get_hub_workflow_version(client: TestClient):
    """Test case for get_hub_workflow_version

    Get hub workflow version detail
    """

    headers = {
        "Authorization": "Bearer special-key",
    }
    # uncomment below to make a request
    #response = client.request(
    #    "GET",
    #    "/api/v1/hub/workflows/{workflowId}/versions/{versionId}".format(workflowId='workflow_id_example', versionId='version_id_example'),
    #    headers=headers,
    #)

    # uncomment below to assert the status code of the HTTP response
    #assert response.status_code == 200


def test_get_hub_workflow_definition(client: TestClient):
    """Test case for get_hub_workflow_definition

    Get hub workflow definition
    """

    headers = {
        "Authorization": "Bearer special-key",
    }
    # uncomment below to make a request
    #response = client.request(
    #    "GET",
    #    "/api/v1/hub/workflows/{workflowId}/versions/{versionId}/definition".format(workflowId='workflow_id_example', versionId='version_id_example'),
    #    headers=headers,
    #)

    # uncomment below to assert the status code of the HTTP response
    #assert response.status_code == 200


def test_import_hub_workflow(client: TestClient):
    """Test case for import_hub_workflow

    Import a hub workflow into the local workspace
    """
    hub_workflow_import_request = {"version_id":"versionId","name":"name","version":"version"}

    headers = {
        "Authorization": "Bearer special-key",
    }
    # uncomment below to make a request
    #response = client.request(
    #    "POST",
    #    "/api/v1/hub/workflows/{workflowId}/import".format(workflowId='workflow_id_example'),
    #    headers=headers,
    #    json=hub_workflow_import_request,
    #)

    # uncomment below to assert the status code of the HTTP response
    #assert response.status_code == 200

