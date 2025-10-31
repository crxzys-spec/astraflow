# coding: utf-8

from fastapi.testclient import TestClient


from pydantic import Field, StrictStr  # noqa: F401
from typing import Optional  # noqa: F401
from typing_extensions import Annotated  # noqa: F401


def test_sse_global_events(client: TestClient):
    """Test case for sse_global_events

    Global Server-Sent Events stream (firehose; no query parameters)
    """

    headers = {
        "last_event_id": 'last_event_id_example',
        "Authorization": "Bearer special-key",
    }
    # uncomment below to make a request
    #response = client.request(
    #    "GET",
    #    "/api/v1/events",
    #    headers=headers,
    #)

    # uncomment below to assert the status code of the HTTP response
    #assert response.status_code == 200

