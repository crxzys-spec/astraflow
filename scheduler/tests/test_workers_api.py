# coding: utf-8

from fastapi.testclient import TestClient


from pydantic import Field, StrictStr  # noqa: F401
from typing import Optional  # noqa: F401
from typing_extensions import Annotated  # noqa: F401
from scheduler_api.models.list_workers200_response import ListWorkers200Response  # noqa: F401
from scheduler_api.models.list_workers200_response_items_inner import ListWorkers200ResponseItemsInner  # noqa: F401
from scheduler_api.models.send_worker_command202_response import SendWorkerCommand202Response  # noqa: F401
from scheduler_api.models.send_worker_command_request import SendWorkerCommandRequest  # noqa: F401
from scheduler_api.models.start_run400_response import StartRun400Response  # noqa: F401


def test_list_workers(client: TestClient):
    """Test case for list_workers

    List workers (scheduler view)
    """
    params = [("queue", 'queue_example'),     ("limit", 50),     ("cursor", 'cursor_example')]
    headers = {
        "Authorization": "Bearer special-key",
    }
    # uncomment below to make a request
    #response = client.request(
    #    "GET",
    #    "/api/v1/workers",
    #    headers=headers,
    #    params=params,
    #)

    # uncomment below to assert the status code of the HTTP response
    #assert response.status_code == 200


def test_get_worker(client: TestClient):
    """Test case for get_worker

    Get worker snapshot
    """

    headers = {
        "Authorization": "Bearer special-key",
    }
    # uncomment below to make a request
    #response = client.request(
    #    "GET",
    #    "/api/v1/workers/{workerName}".format(workerName='worker_name_example'),
    #    headers=headers,
    #)

    # uncomment below to assert the status code of the HTTP response
    #assert response.status_code == 200


def test_send_worker_command(client: TestClient):
    """Test case for send_worker_command

    Enqueue admin command (drain/rebind/pkg.install/pkg.uninstall)
    """
    send_worker_command_request = scheduler_api.SendWorkerCommandRequest()

    headers = {
        "idempotency_key": 'idempotency_key_example',
        "Authorization": "Bearer special-key",
    }
    # uncomment below to make a request
    #response = client.request(
    #    "POST",
    #    "/api/v1/workers/{workerName}/commands".format(workerName='worker_name_example'),
    #    headers=headers,
    #    json=send_worker_command_request,
    #)

    # uncomment below to assert the status code of the HTTP response
    #assert response.status_code == 200

