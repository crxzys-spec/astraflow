# coding: utf-8

from fastapi.testclient import TestClient

import scheduler_api


from pydantic import Field, StrictStr  # noqa: F401
from typing import Optional  # noqa: F401
from typing_extensions import Annotated  # noqa: F401
from scheduler_api.models.list_workflows200_response import ListWorkflows200Response  # noqa: F401
from scheduler_api.models.list_workflows200_response_items_inner import ListWorkflows200ResponseItemsInner  # noqa: F401
from scheduler_api.models.persist_workflow201_response import PersistWorkflow201Response  # noqa: F401
from scheduler_api.models.start_run400_response import StartRun400Response  # noqa: F401


def test_list_workflows(client: TestClient):
    """Test case for list_workflows

    List stored workflows (paginated)
    """
    params = [("limit", 50),     ("cursor", 'cursor_example')]
    headers = {
        "Authorization": "Bearer special-key",
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


def test_persist_workflow(client: TestClient):
    """Test case for persist_workflow

    Persist a workflow for editor storage (no versioning)
    """
    list_workflows200_response_items_inner = scheduler_api.ListWorkflows200ResponseItemsInner(
        id="wf-1",
        schema_version="2025-10",
        metadata={
            "name": "workflow",
            "namespace": "default",
            "originId": "wf-1",
        },
        nodes=[
            {
                "id": "node-1",
                "type": "example.node",
                "package": {"name": "example", "version": "1.0.0"},
                "status": "published",
                "category": "test",
                "label": "Node",
                "position": {"x": 0, "y": 0},
            }
        ],
        edges=[],
    )

    headers = {
        "idempotency_key": 'idempotency_key_example',
        "Authorization": "Bearer special-key",
    }
    # uncomment below to make a request
    #response = client.request(
    #    "POST",
    #    "/api/v1/workflows",
    #    headers=headers,
    #    json=list_workflows200_response_items_inner,
    #)

    # uncomment below to assert the status code of the HTTP response
    #assert response.status_code == 200


def test_get_workflow(client: TestClient):
    """Test case for get_workflow

    Read stored workflow (latest)
    """

    headers = {
        "Authorization": "Bearer special-key",
    }
    # uncomment below to make a request
    #response = client.request(
    #    "GET",
    #    "/api/v1/workflows/{workflowId}".format(workflowId='workflow_id_example'),
    #    headers=headers,
    #)

    # uncomment below to assert the status code of the HTTP response
    #assert response.status_code == 200

