# coding: utf-8

from fastapi.testclient import TestClient


from scheduler_api.models.error import Error  # noqa: F401
from scheduler_api.models.hub_account import HubAccount  # noqa: F401


def test_get_hub_account(client: TestClient):
    """Test case for get_hub_account

    Get hub account profile via scheduler proxy
    """

    headers = {
        "Authorization": "Bearer special-key",
    }
    # uncomment below to make a request
    #response = client.request(
    #    "GET",
    #    "/api/v1/hub/account",
    #    headers=headers,
    #)

    # uncomment below to assert the status code of the HTTP response
    #assert response.status_code == 200

