"""Ubiquity AirOS tests."""

from http.cookies import SimpleCookie
import json
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import aiofiles


async def _read_fixture(fixture: str = "ap-ptp"):
    """Read fixture file per device type."""
    fixture_dir = os.path.join(os.path.dirname(__file__), "..", "fixtures")
    path = os.path.join(fixture_dir, f"{fixture}.json")
    try:
        async with aiofiles.open(path, encoding="utf-8") as f:
            return json.loads(await f.read())
    except FileNotFoundError:
        pytest.fail(f"Fixture file not found: {path}")
    except json.JSONDecodeError as e:
        pytest.fail(f"Invalid JSON in fixture file {path}: {e}")


@pytest.mark.parametrize("mode", ["ap-ptp", "sta-ptp"])
@pytest.mark.asyncio
async def test_ap(airos_device, base_url, mode):
    """Test device operation."""
    cookie = SimpleCookie()
    cookie["session_id"] = "test-cookie"
    cookie["AIROS_TOKEN"] = "abc123"

    # --- Prepare fake POST /api/auth response with cookies ---
    mock_login_response = MagicMock()
    mock_login_response.__aenter__.return_value = mock_login_response
    mock_login_response.text = AsyncMock(return_value="{}")
    mock_login_response.status = 200
    mock_login_response.cookies = cookie
    mock_login_response.headers = {"X-CSRF-ID": "test-csrf-token"}
    # --- Prepare fake GET /api/status response ---
    fixture_data = await _read_fixture(mode)
    mock_status_payload = fixture_data
    mock_status_response = MagicMock()
    mock_status_response.__aenter__.return_value = mock_status_response
    mock_status_response.text = AsyncMock(return_value=json.dumps(fixture_data))
    mock_status_response.status = 200
    mock_status_response.json = AsyncMock(return_value=mock_status_payload)

    with (
        patch.object(airos_device.session, "post", return_value=mock_login_response),
        patch.object(airos_device.session, "get", return_value=mock_status_response),
    ):
        assert await airos_device.login()
        status = await airos_device.status()

        # Verify the fixture returns the correct mode
        assert status.get("wireless", {}).get("mode") == mode
