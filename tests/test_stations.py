"""Ubiquity AirOS tests."""

from http.cookies import SimpleCookie
import json
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import aiofiles


async def _read_fixture(fixture: str = "ap-ptp"):
    """Read fixture file per device type."""
    path = os.path.join(os.path.dirname(__file__), f"../fixtures/{fixture}.json")
    async with aiofiles.open(path, encoding="utf-8") as f:
        return json.loads(await f.read())


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
    mock_login_response.text = "{}"
    mock_login_response.status = 200
    mock_login_response.cookies = cookie

    # --- Prepare fake GET /api/status response ---
    mock_status_payload = {"mode": await _read_fixture(fixture=mode)}
    mock_status_response = MagicMock()
    mock_status_response.__aenter__.return_value = mock_status_response
    mock_status_response.text = json.dumps(await _read_fixture(mode))
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
