# coding: utf-8

from fastapi.testclient import TestClient


from pydantic import StrictStr  # noqa: F401
from typing import Any  # noqa: F401
from hub_api.models.access_token import AccessToken  # noqa: F401
from hub_api.models.access_token_create_request import AccessTokenCreateRequest  # noqa: F401
from hub_api.models.access_token_list import AccessTokenList  # noqa: F401
from hub_api.models.error import Error  # noqa: F401


def test_list_tokens(client: TestClient):
    """Test case for list_tokens

    List access tokens
    """

    headers = {
        "Authorization": "Bearer special-key",
    }
    # uncomment below to make a request
    #response = client.request(
    #    "GET",
    #    "/api/v1/tokens",
    #    headers=headers,
    #)

    # uncomment below to assert the status code of the HTTP response
    #assert response.status_code == 200


def test_create_publish_token(client: TestClient):
    """Test case for create_publish_token

    Create publish token
    """
    access_token_create_request = {"label":"label","scopes":["read","read"],"package_name":"packageName","expires_at":"2000-01-23T04:56:07.000+00:00"}

    headers = {
        "Authorization": "Bearer special-key",
    }
    # uncomment below to make a request
    #response = client.request(
    #    "POST",
    #    "/api/v1/tokens/publish",
    #    headers=headers,
    #    json=access_token_create_request,
    #)

    # uncomment below to assert the status code of the HTTP response
    #assert response.status_code == 200


def test_revoke_token(client: TestClient):
    """Test case for revoke_token

    Revoke access token
    """

    headers = {
        "Authorization": "Bearer special-key",
    }
    # uncomment below to make a request
    #response = client.request(
    #    "DELETE",
    #    "/api/v1/tokens/{tokenId}".format(tokenId='token_id_example'),
    #    headers=headers,
    #)

    # uncomment below to assert the status code of the HTTP response
    #assert response.status_code == 200

