# coding: utf-8

from fastapi.testclient import TestClient


from pydantic import StrictStr  # noqa: F401
from typing import Any  # noqa: F401
from hub_api.models.error import Error  # noqa: F401
from hub_api.models.team import Team  # noqa: F401
from hub_api.models.team_create_request import TeamCreateRequest  # noqa: F401
from hub_api.models.team_list import TeamList  # noqa: F401
from hub_api.models.team_member import TeamMember  # noqa: F401
from hub_api.models.team_member_list import TeamMemberList  # noqa: F401
from hub_api.models.team_member_request import TeamMemberRequest  # noqa: F401


def test_list_organization_teams(client: TestClient):
    """Test case for list_organization_teams

    List organization teams
    """

    headers = {
        "Authorization": "Bearer special-key",
    }
    # uncomment below to make a request
    #response = client.request(
    #    "GET",
    #    "/api/v1/orgs/{orgId}/teams".format(orgId='org_id_example'),
    #    headers=headers,
    #)

    # uncomment below to assert the status code of the HTTP response
    #assert response.status_code == 200


def test_create_team(client: TestClient):
    """Test case for create_team

    Create team
    """
    team_create_request = {"name":"name","slug":"slug"}

    headers = {
        "Authorization": "Bearer special-key",
    }
    # uncomment below to make a request
    #response = client.request(
    #    "POST",
    #    "/api/v1/orgs/{orgId}/teams".format(orgId='org_id_example'),
    #    headers=headers,
    #    json=team_create_request,
    #)

    # uncomment below to assert the status code of the HTTP response
    #assert response.status_code == 200


def test_list_team_members(client: TestClient):
    """Test case for list_team_members

    List team members
    """

    headers = {
        "Authorization": "Bearer special-key",
    }
    # uncomment below to make a request
    #response = client.request(
    #    "GET",
    #    "/api/v1/orgs/{orgId}/teams/{teamId}/members".format(orgId='org_id_example', teamId='team_id_example'),
    #    headers=headers,
    #)

    # uncomment below to assert the status code of the HTTP response
    #assert response.status_code == 200


def test_add_team_member(client: TestClient):
    """Test case for add_team_member

    Add team member
    """
    team_member_request = {"user_id":"userId"}

    headers = {
        "Authorization": "Bearer special-key",
    }
    # uncomment below to make a request
    #response = client.request(
    #    "POST",
    #    "/api/v1/orgs/{orgId}/teams/{teamId}/members".format(orgId='org_id_example', teamId='team_id_example'),
    #    headers=headers,
    #    json=team_member_request,
    #)

    # uncomment below to assert the status code of the HTTP response
    #assert response.status_code == 200


def test_remove_team_member(client: TestClient):
    """Test case for remove_team_member

    Remove team member
    """

    headers = {
        "Authorization": "Bearer special-key",
    }
    # uncomment below to make a request
    #response = client.request(
    #    "DELETE",
    #    "/api/v1/orgs/{orgId}/teams/{teamId}/members/{userId}".format(orgId='org_id_example', teamId='team_id_example', userId='user_id_example'),
    #    headers=headers,
    #)

    # uncomment below to assert the status code of the HTTP response
    #assert response.status_code == 200

