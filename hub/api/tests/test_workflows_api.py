# coding: utf-8

from fastapi.testclient import TestClient


from pydantic import Field, StrictStr  # noqa: F401
from typing import Any, Optional  # noqa: F401
from typing_extensions import Annotated  # noqa: F401
from hub_api.models.hub_workflow_detail import HubWorkflowDetail  # noqa: F401
from hub_api.models.workflow_list_response import WorkflowListResponse  # noqa: F401


def test_list_workflows(client: TestClient):
    """Test case for list_workflows

    List workflows
    """
    params = [("q", 'q_example'),     ("tag", 'tag_example'),     ("owner", 'owner_example'),     ("page", 1),     ("page_size", 20)]
    headers = {
    }
    # uncomment below to make a request
    #response = client.request(
    #    "GET",
    #    "/api/v1/workflows",
    #    headers=headers,
    #    params=params,
    #)

    # uncomment below to assert the status code of the HTTP response
    #assert response.status_code == 200


def test_get_workflow(client: TestClient):
    """Test case for get_workflow

    Get workflow detail
    """

    headers = {
    }
    # uncomment below to make a request
    #response = client.request(
    #    "GET",
    #    "/api/v1/workflows/{workflowId}".format(workflowId='workflow_id_example'),
    #    headers=headers,
    #)

    # uncomment below to assert the status code of the HTTP response
    #assert response.status_code == 200

