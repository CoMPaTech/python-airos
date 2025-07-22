"""Ubiquity AirOS tests."""

from http.cookies import SimpleCookie
import json
import os
from unittest.mock import AsyncMock, MagicMock, patch

from airos.airos8data import AirOSData
import airos.exceptions
import pytest

import aiofiles
import aiohttp


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
async def test_ap_object(airos_device, base_url, mode):
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
        status: AirOSData = await airos_device.status()  # Implies return_json = False

        # Verify the fixture returns the correct mode
        assert status.wireless.mode.value == mode


@pytest.mark.asyncio
async def test_reconnect(airos_device, base_url):
    """Test reconnect client."""
    # --- Prepare fake POST /api/stakick response ---
    mock_stakick_response = MagicMock()
    mock_stakick_response.__aenter__.return_value = mock_stakick_response
    mock_stakick_response.status = 200

    with (
        patch.object(airos_device.session, "post", return_value=mock_stakick_response),
        patch.object(airos_device, "connected", True),
    ):
        assert await airos_device.stakick("01:23:45:67:89:aB")


@pytest.mark.asyncio
async def test_ap_corners(airos_device, base_url, mode="ap-ptp"):
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

    with (
        patch.object(airos_device.session, "post", return_value=mock_login_response),
        patch.object(airos_device, "_use_json_for_login_post", return_value=True),
    ):
        assert await airos_device.login()

    mock_login_response.cookies = {}
    with (
        patch.object(airos_device.session, "post", return_value=mock_login_response),
    ):
        try:
            assert await airos_device.login()
            assert False
        except airos.exceptions.ConnectionSetupError:
            assert True

    mock_login_response.cookies = cookie
    mock_login_response.headers = {}
    with (
        patch.object(airos_device.session, "post", return_value=mock_login_response),
    ):
        result = await airos_device.login()
        assert result is None

    mock_login_response.headers = {"X-CSRF-ID": "test-csrf-token"}
    mock_login_response.text = AsyncMock(return_value="abc123")
    with (
        patch.object(airos_device.session, "post", return_value=mock_login_response),
    ):
        try:
            assert await airos_device.login()
            assert False
        except airos.exceptions.DataMissingError:
            assert True

    mock_login_response.text = AsyncMock(return_value="{}")
    mock_login_response.status = 400
    with (
        patch.object(airos_device.session, "post", return_value=mock_login_response),
    ):
        try:
            assert await airos_device.login()
            assert False
        except airos.exceptions.ConnectionAuthenticationError:
            assert True

    mock_login_response.status = 200
    with patch.object(airos_device.session, "post", side_effect=aiohttp.ClientError):
        try:
            assert await airos_device.login()
            assert False
        except airos.exceptions.DeviceConnectionError:
            assert True
