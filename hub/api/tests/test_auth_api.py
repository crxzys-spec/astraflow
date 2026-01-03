# coding: utf-8

from fastapi.testclient import TestClient


from hub_api.models.auth_login_request import AuthLoginRequest  # noqa: F401
from hub_api.models.auth_register_request import AuthRegisterRequest  # noqa: F401
from hub_api.models.auth_response import AuthResponse  # noqa: F401
from hub_api.models.error import Error  # noqa: F401


def test_register_account(client: TestClient):
    """Test case for register_account

    Register a new account
    """
    auth_register_request = {"password":"password","display_name":"displayName","email":"email","username":"username"}

    headers = {
    }
    # uncomment below to make a request
    #response = client.request(
    #    "POST",
    #    "/api/v1/auth/register",
    #    headers=headers,
    #    json=auth_register_request,
    #)

    # uncomment below to assert the status code of the HTTP response
    #assert response.status_code == 200


def test_login_account(client: TestClient):
    """Test case for login_account

    Login with username and password
    """
    auth_login_request = {"password":"password","username":"username"}

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

