# coding: utf-8

from fastapi.testclient import TestClient


from hub_api.models.account import Account  # noqa: F401
from hub_api.models.error import Error  # noqa: F401


def test_get_account(client: TestClient):
    """Test case for get_account

    Get current account
    """

    headers = {
        "Authorization": "Bearer special-key",
    }
    # uncomment below to make a request
    #response = client.request(
    #    "GET",
    #    "/api/v1/account",
    #    headers=headers,
    #)

    # uncomment below to assert the status code of the HTTP response
    #assert response.status_code == 200

