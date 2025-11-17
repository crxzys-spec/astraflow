# coding: utf-8

from fastapi.testclient import TestClient


from pydantic import Field, StrictStr  # noqa: F401
from typing import Optional  # noqa: F401
from typing_extensions import Annotated  # noqa: F401
from scheduler_api.models.list_audit_events200_response import ListAuditEvents200Response  # noqa: F401


def test_list_audit_events(client: TestClient):
    """Test case for list_audit_events

    List audit events
    """
    params = [("limit", 50),     ("cursor", 'cursor_example')]
    headers = {
        "Authorization": "Bearer special-key",
    }
    # uncomment below to make a request
    #response = client.request(
    #    "GET",
    #    "/api/v1/audit-events",
    #    headers=headers,
    #    params=params,
    #)

    # uncomment below to assert the status code of the HTTP response
    #assert response.status_code == 200

