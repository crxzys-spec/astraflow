# coding: utf-8

from fastapi.testclient import TestClient


from pydantic import Field, StrictStr  # noqa: F401
from typing import Optional  # noqa: F401
from typing_extensions import Annotated  # noqa: F401
from scheduler_api.models.catalog_node_search_response import CatalogNodeSearchResponse  # noqa: F401
from scheduler_api.models.error import Error  # noqa: F401


def test_search_catalog_nodes(client: TestClient):
    """Test case for search_catalog_nodes

    Search catalog nodes (system + worker capabilities)
    """
    params = [("q", 'q_example'),     ("package", 'package_example')]
    headers = {
        "Authorization": "Bearer special-key",
    }
    # uncomment below to make a request
    #response = client.request(
    #    "GET",
    #    "/api/v1/catalog/nodes/search",
    #    headers=headers,
    #    params=params,
    #)

    # uncomment below to assert the status code of the HTTP response
    #assert response.status_code == 200

