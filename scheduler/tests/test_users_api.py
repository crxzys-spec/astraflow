# coding: utf-8

from fastapi.testclient import TestClient

import scheduler_api


from pydantic import StrictStr  # noqa: F401
from typing import Any  # noqa: F401
from scheduler_api.models.add_user_role_request import AddUserRoleRequest  # noqa: F401
from scheduler_api.models.create_user201_response import CreateUser201Response  # noqa: F401
from scheduler_api.models.create_user_request import CreateUserRequest  # noqa: F401
from scheduler_api.models.list_users200_response import ListUsers200Response  # noqa: F401
from scheduler_api.models.reset_user_password_request import ResetUserPasswordRequest  # noqa: F401


def test_list_users(client: TestClient):
    """Test case for list_users

    List users and their roles
    """

    headers = {
        "Authorization": "Bearer special-key",
    }
    # uncomment below to make a request
    #response = client.request(
    #    "GET",
    #    "/api/v1/users",
    #    headers=headers,
    #)

    # uncomment below to assert the status code of the HTTP response
    #assert response.status_code == 200


def test_create_user(client: TestClient):
    """Test case for create_user

    Create a new user
    """
    create_user_request = scheduler_api.CreateUserRequest(
        username="user",
        display_name="Test User",
        password="password",
    )

    headers = {
        "Authorization": "Bearer special-key",
    }
    # uncomment below to make a request
    #response = client.request(
    #    "POST",
    #    "/api/v1/users",
    #    headers=headers,
    #    json=create_user_request,
    #)

    # uncomment below to assert the status code of the HTTP response
    #assert response.status_code == 200


def test_reset_user_password(client: TestClient):
    """Test case for reset_user_password

    Reset user password
    """
    reset_user_password_request = scheduler_api.ResetUserPasswordRequest(password="new-password")

    headers = {
        "Authorization": "Bearer special-key",
    }
    # uncomment below to make a request
    #response = client.request(
    #    "POST",
    #    "/api/v1/users/{userId}/password".format(userId='user_id_example'),
    #    headers=headers,
    #    json=reset_user_password_request,
    #)

    # uncomment below to assert the status code of the HTTP response
    #assert response.status_code == 200


def test_add_user_role(client: TestClient):
    """Test case for add_user_role

    Assign role to user
    """
    add_user_role_request = scheduler_api.AddUserRoleRequest(role="admin")

    headers = {
        "Authorization": "Bearer special-key",
    }
    # uncomment below to make a request
    #response = client.request(
    #    "POST",
    #    "/api/v1/users/{userId}/roles".format(userId='user_id_example'),
    #    headers=headers,
    #    json=add_user_role_request,
    #)

    # uncomment below to assert the status code of the HTTP response
    #assert response.status_code == 200


def test_remove_user_role(client: TestClient):
    """Test case for remove_user_role

    Remove role from user
    """

    headers = {
        "Authorization": "Bearer special-key",
    }
    # uncomment below to make a request
    #response = client.request(
    #    "DELETE",
    #    "/api/v1/users/{userId}/roles/{role}".format(userId='user_id_example', role='role_example'),
    #    headers=headers,
    #)

    # uncomment below to assert the status code of the HTTP response
    #assert response.status_code == 200
