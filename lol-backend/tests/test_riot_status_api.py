"""Tests for Riot status API endpoints."""

from unittest.mock import AsyncMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.endpoints import riot_status
from app.services.riot_api_client import RiotAPIError


def create_test_app():
    app = FastAPI()
    app.include_router(riot_status.router)
    return app


def test_get_riot_status_returns_platform_data():
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.get_lol_status.return_value = {
        "id": "TW2",
        "name": "Taiwan",
        "locales": ["zh_TW"],
        "maintenances": [],
        "incidents": [],
    }

    app = create_test_app()
    app.dependency_overrides[riot_status.get_riot_client_dependency] = lambda: mock_client

    with TestClient(app) as client:
        response = client.get("/riot/status/tw2")

    assert response.status_code == 200
    assert response.json()["id"] == "TW2"
    mock_client.get_lol_status.assert_awaited_once_with("tw2")
    app.dependency_overrides.clear()


def test_get_riot_status_returns_404_when_platform_missing():
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.get_lol_status.return_value = None

    app = create_test_app()
    app.dependency_overrides[riot_status.get_riot_client_dependency] = lambda: mock_client

    with TestClient(app) as client:
        response = client.get("/riot/status/bad1")

    assert response.status_code == 404
    app.dependency_overrides.clear()


def test_get_riot_status_maps_riot_errors():
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.get_lol_status.side_effect = RiotAPIError(403, "Invalid API key or forbidden")

    app = create_test_app()
    app.dependency_overrides[riot_status.get_riot_client_dependency] = lambda: mock_client

    with TestClient(app) as client:
        response = client.get("/riot/status/tw2")

    assert response.status_code == 403
    assert "Invalid API key" in response.json()["detail"]
    app.dependency_overrides.clear()
