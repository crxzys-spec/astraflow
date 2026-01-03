# coding: utf-8

from fastapi.testclient import TestClient


from pydantic import StrictStr  # noqa: F401
from typing import Any  # noqa: F401
from hub_api.models.error import Error  # noqa: F401
from hub_api.models.organization import Organization  # noqa: F401
from hub_api.models.organization_create_request import OrganizationCreateRequest  # noqa: F401
from hub_api.models.organization_list import OrganizationList  # noqa: F401
from hub_api.models.organization_member import OrganizationMember  # noqa: F401
from hub_api.models.organization_member_list import OrganizationMemberList  # noqa: F401
from hub_api.models.organization_member_request import OrganizationMemberRequest  # noqa: F401


def test_list_organizations(client: TestClient):
    """Test case for list_organizations

    List organizations
    """

    headers = {
        "Authorization": "Bearer special-key",
    }
    # uncomment below to make a request
    #response = client.request(
    #    "GET",
    #    "/api/v1/orgs",
    #    headers=headers,
    #)

    # uncomment below to assert the status code of the HTTP response
    #assert response.status_code == 200


def test_create_organization(client: TestClient):
    """Test case for create_organization

    Create organization
    """
    organization_create_request = {"name":"name","slug":"slug"}

    headers = {
        "Authorization": "Bearer special-key",
    }
    # uncomment below to make a request
    #response = client.request(
    #    "POST",
    #    "/api/v1/orgs",
    #    headers=headers,
    #    json=organization_create_request,
    #)

    # uncomment below to assert the status code of the HTTP response
    #assert response.status_code == 200


def test_get_organization(client: TestClient):
    """Test case for get_organization

    Get organization
    """

    headers = {
        "Authorization": "Bearer special-key",
    }
    # uncomment below to make a request
    #response = client.request(
    #    "GET",
    #    "/api/v1/orgs/{orgId}".format(orgId='org_id_example'),
    #    headers=headers,
    #)

    # uncomment below to assert the status code of the HTTP response
    #assert response.status_code == 200


def test_list_organization_members(client: TestClient):
    """Test case for list_organization_members

    List organization members
    """

    headers = {
        "Authorization": "Bearer special-key",
    }
    # uncomment below to make a request
    #response = client.request(
    #    "GET",
    #    "/api/v1/orgs/{orgId}/members".format(orgId='org_id_example'),
    #    headers=headers,
    #)

    # uncomment below to assert the status code of the HTTP response
    #assert response.status_code == 200


def test_add_organization_member(client: TestClient):
    """Test case for add_organization_member

    Add organization member
    """
    organization_member_request = {"role":"owner","user_id":"userId"}

    headers = {
        "Authorization": "Bearer special-key",
    }
    # uncomment below to make a request
    #response = client.request(
    #    "POST",
    #    "/api/v1/orgs/{orgId}/members".format(orgId='org_id_example'),
    #    headers=headers,
    #    json=organization_member_request,
    #)

    # uncomment below to assert the status code of the HTTP response
    #assert response.status_code == 200


def test_remove_organization_member(client: TestClient):
    """Test case for remove_organization_member

    Remove organization member
    """

    headers = {
        "Authorization": "Bearer special-key",
    }
    # uncomment below to make a request
    #response = client.request(
    #    "DELETE",
    #    "/api/v1/orgs/{orgId}/members/{userId}".format(orgId='org_id_example', userId='user_id_example'),
    #    headers=headers,
    #)

    # uncomment below to assert the status code of the HTTP response
    #assert response.status_code == 200

