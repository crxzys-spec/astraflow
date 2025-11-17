# coding: utf-8

from fastapi.testclient import TestClient


from scheduler_api.models.auth_login200_response import AuthLogin200Response  # noqa: F401
from scheduler_api.models.auth_login401_response import AuthLogin401Response  # noqa: F401
from scheduler_api.models.auth_login_request import AuthLoginRequest  # noqa: F401


def test_auth_login(client: TestClient):
    """Test case for auth_login

    Exchange username/password for a JWT
    """
    auth_login_request = scheduler_api.AuthLoginRequest()

    headers = {
    }
    # uncomment below to make a request
    #response = client.request(
    #    "POST",
    #    "/api/v1/auth/login",
    #    headers=headers,
    #    json=auth_login_request,
    #)

    # uncomment below to assert the status code of the HTTP response
    #assert response.status_code == 200

