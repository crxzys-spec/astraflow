# coding: utf-8

from fastapi.testclient import TestClient

import scheduler_api


from pydantic import Field, StrictStr, field_validator  # noqa: F401
from typing import Optional  # noqa: F401
from typing_extensions import Annotated  # noqa: F401
from scheduler_api.models.list_runs200_response import ListRuns200Response  # noqa: F401
from scheduler_api.models.list_runs200_response_items_inner import ListRuns200ResponseItemsInner  # noqa: F401
from scheduler_api.models.start_run202_response import StartRun202Response  # noqa: F401
from scheduler_api.models.start_run400_response import StartRun400Response  # noqa: F401
from scheduler_api.models.start_run_request import StartRunRequest  # noqa: F401
from scheduler_api.models.start_run_request_workflow import StartRunRequestWorkflow  # noqa: F401


def test_list_runs(client: TestClient):
    """Test case for list_runs

    List runs (paginated)
    """
    params = [("limit", 50),     ("cursor", 'cursor_example'),     ("status", 'status_example'),     ("client_id", 'client_id_example')]
    headers = {
        "Authorization": "Bearer special-key",
    }
    # uncomment below to make a request
    #response = client.request(
    #    "GET",
    #    "/api/v1/runs",
    #    headers=headers,
    #    params=params,
    #)

    # uncomment below to assert the status code of the HTTP response
    #assert response.status_code == 200


def test_start_run(client: TestClient):
    """Test case for start_run

    Start a run using the in-memory workflow snapshot
    """
    workflow = StartRunRequestWorkflow.from_dict(
        {
            "id": "wf-1",
            "schemaVersion": "2025-10",
            "metadata": {
                "name": "workflow",
                "namespace": "default",
                "originId": "wf-1",
            },
            "nodes": [
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
            "edges": [],
        }
    )
    start_run_request = scheduler_api.StartRunRequest(
        workflow=workflow,
        client_id="client-1",
    )

    headers = {
        "idempotency_key": 'idempotency_key_example',
        "Authorization": "Bearer special-key",
    }
    # uncomment below to make a request
    #response = client.request(
    #    "POST",
    #    "/api/v1/runs",
    #    headers=headers,
    #    json=start_run_request,
    #)

    # uncomment below to assert the status code of the HTTP response
    #assert response.status_code == 200


def test_get_run(client: TestClient):
    """Test case for get_run

    Get run summary
    """

    headers = {
        "Authorization": "Bearer special-key",
    }
    # uncomment below to make a request
    #response = client.request(
    #    "GET",
    #    "/api/v1/runs/{runId}".format(runId='run_id_example'),
    #    headers=headers,
    #)

    # uncomment below to assert the status code of the HTTP response
    #assert response.status_code == 200


def test_get_run_definition(client: TestClient):
    """Test case for get_run_definition

    Get the immutable workflow snapshot used by this run
    """

    headers = {
        "Authorization": "Bearer special-key",
    }
    # uncomment below to make a request
    #response = client.request(
    #    "GET",
    #    "/api/v1/runs/{runId}/definition".format(runId='run_id_example'),
    #    headers=headers,
    #)

    # uncomment below to assert the status code of the HTTP response
    #assert response.status_code == 200

