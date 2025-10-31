# coding: utf-8

from fastapi.testclient import TestClient


from pydantic import Field, StrictStr, field_validator  # noqa: F401
from typing import Optional  # noqa: F401
from typing_extensions import Annotated  # noqa: F401
from scheduler_api.models.get_node200_response import GetNode200Response  # noqa: F401
from scheduler_api.models.list_node_categories200_response import ListNodeCategories200Response  # noqa: F401
from scheduler_api.models.list_nodes200_response import ListNodes200Response  # noqa: F401
from scheduler_api.models.start_run400_response import StartRun400Response  # noqa: F401


def test_list_nodes(client: TestClient):
    """Test case for list_nodes

    List available nodes (catalog)
    """
    params = [("limit", 50),     ("cursor", 'cursor_example'),     ("category", 'category_example'),     ("status", 'status_example'),     ("tag", 'tag_example'),     ("q", 'q_example')]
    headers = {
        "Authorization": "Bearer special-key",
    }
    # uncomment below to make a request
    #response = client.request(
    #    "GET",
    #    "/api/v1/nodes",
    #    headers=headers,
    #    params=params,
    #)

    # uncomment below to assert the status code of the HTTP response
    #assert response.status_code == 200


def test_get_node(client: TestClient):
    """Test case for get_node

    Get a node definition
    """

    headers = {
        "Authorization": "Bearer special-key",
    }
    # uncomment below to make a request
    #response = client.request(
    #    "GET",
    #    "/api/v1/nodes/{nodeId}".format(nodeId='node_id_example'),
    #    headers=headers,
    #)

    # uncomment below to assert the status code of the HTTP response
    #assert response.status_code == 200


def test_list_node_categories(client: TestClient):
    """Test case for list_node_categories

    List node categories
    """

    headers = {
        "Authorization": "Bearer special-key",
    }
    # uncomment below to make a request
    #response = client.request(
    #    "GET",
    #    "/api/v1/nodes:categories",
    #    headers=headers,
    #)

    # uncomment below to assert the status code of the HTTP response
    #assert response.status_code == 200

