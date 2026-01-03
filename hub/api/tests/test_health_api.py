# coding: utf-8

from fastapi.testclient import TestClient


from hub_api.models.health_status import HealthStatus  # noqa: F401


def test_get_health(client: TestClient):
    """Test case for get_health

    Health check
    """

    headers = {
    }
    # uncomment below to make a request
    #response = client.request(
    #    "GET",
    #    "/health",
    #    headers=headers,
    #)

    # uncomment below to assert the status code of the HTTP response
    #assert response.status_code == 200

