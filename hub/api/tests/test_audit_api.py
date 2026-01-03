# coding: utf-8

from fastapi.testclient import TestClient


from pydantic import Field, StrictStr  # noqa: F401
from typing import Optional  # noqa: F401
from typing_extensions import Annotated  # noqa: F401
from hub_api.models.audit_event_list import AuditEventList  # noqa: F401
from hub_api.models.error import Error  # noqa: F401


def test_list_audit_events(client: TestClient):
    """Test case for list_audit_events

    List audit events
    """
    params = [("actor", 'actor_example'),     ("action", 'action_example'),     ("limit", 50)]
    headers = {
        "Authorization": "Bearer special-key",
    }
    # uncomment below to make a request
    #response = client.request(
    #    "GET",
    #    "/api/v1/audit",
    #    headers=headers,
    #    params=params,
    #)

    # uncomment below to assert the status code of the HTTP response
    #assert response.status_code == 200

