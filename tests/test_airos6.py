"""Additional tests for airOS6 module."""

from http.cookies import SimpleCookie
import json
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
from mashumaro.exceptions import MissingField
import pytest

from airos.airos6 import AirOS6
import airos.exceptions


@pytest.mark.skip(reason="broken, needs investigation")
@pytest.mark.asyncio
async def test_login_no_csrf_token(airos6_device: AirOS6) -> None:
    """Test login response without a CSRF token header."""
    cookie = SimpleCookie()
    cookie["AIROS_TOKEN"] = "abc"

    mock_login_response = MagicMock()
    mock_login_response.__aenter__.return_value = mock_login_response
    mock_login_response.text = AsyncMock(return_value="{}")
    mock_login_response.status = 200
    mock_login_response.cookies = cookie  # Use the SimpleCookie object
    mock_login_response.headers = {}  # Simulate missing X-CSRF-ID

    with patch.object(
        airos6_device.session, "request", return_value=mock_login_response
    ):
        # We expect a return of None as the CSRF token is missing
        await airos6_device.login()


@pytest.mark.asyncio
async def test_login_connection_error(airos6_device: AirOS6) -> None:
    """Test aiohttp ClientError during login attempt."""
    with (
        patch.object(airos6_device.session, "request", side_effect=aiohttp.ClientError),
        pytest.raises(airos.exceptions.AirOSDeviceConnectionError),
    ):
        await airos6_device.login()


# --- Tests for status() and derived_data() logic ---
@pytest.mark.asyncio
async def test_status_when_not_connected(airos6_device: AirOS6) -> None:
    """Test calling status() before a successful login."""
    airos6_device.connected = False  # Ensure connected state is false
    with pytest.raises(airos.exceptions.AirOSDeviceConnectionError):
        await airos6_device.status()


# pylint: disable=pointless-string-statement
'''
@pytest.mark.asyncio
async def test_status_non_200_response(airos6_device: AirOS6) -> None:
    """Test status() with a non-successful HTTP response."""
    airos6_device.connected = True
    mock_status_response = MagicMock()
    mock_status_response.__aenter__.return_value = mock_status_response
    mock_status_response.text = AsyncMock(return_value="Error")
    mock_status_response.status = 500  # Simulate server error

    with (
        patch.object(airos6_device.session, "request", return_value=mock_status_response),
        pytest.raises(airos.exceptions.AirOSDeviceConnectionError),
    ):
        await airos6_device.status()
'''


@pytest.mark.asyncio
async def test_status_invalid_json_response(airos6_device: AirOS6) -> None:
    """Test status() with a response that is not valid JSON."""
    airos6_device.connected = True
    mock_status_response = MagicMock()
    mock_status_response.__aenter__.return_value = mock_status_response
    mock_status_response.text = AsyncMock(return_value="This is not JSON")
    mock_status_response.status = 200

    with (
        patch.object(
            airos6_device.session, "request", return_value=mock_status_response
        ),
        pytest.raises(airos.exceptions.AirOSDataMissingError),
    ):
        await airos6_device.status()


@pytest.mark.asyncio
async def test_status_missing_interface_key_data(airos6_device: AirOS6) -> None:
    """Test status() with a response missing critical data fields."""
    airos6_device.connected = True
    # The derived_data() function is called with a mocked response
    mock_status_response = MagicMock()
    mock_status_response.__aenter__.return_value = mock_status_response
    mock_status_response.text = AsyncMock(
        return_value=json.dumps({"system": {}})
    )  # Missing 'interfaces'
    mock_status_response.status = 200

    with (
        patch.object(
            airos6_device.session, "request", return_value=mock_status_response
        ),
        pytest.raises(airos.exceptions.AirOSKeyDataMissingError),
    ):
        await airos6_device.status()


@pytest.mark.asyncio
async def test_derived_data_no_interfaces_key(airos6_device: AirOS6) -> None:
    """Test derived_data() with a response that has no 'interfaces' key."""
    # This will directly test the 'if not interfaces:' branch (line 206)
    with pytest.raises(airos.exceptions.AirOSKeyDataMissingError):
        airos6_device.derived_data({})


@pytest.mark.asyncio
async def test_derived_data_no_br0_eth0_ath0(airos6_device: AirOS6) -> None:
    """Test derived_data() with an unexpected interface list, to test the fallback logic."""
    fixture_data = {
        "host": {
            "fwversion": "v8.0.0",
        },
        "interfaces": [
            {"ifname": "wan0", "enabled": True, "hwaddr": "11:22:33:44:55:66"}
        ],
    }

    adjusted_data = airos6_device.derived_data(fixture_data)
    assert adjusted_data["derived"]["mac_interface"] == "wan0"
    assert adjusted_data["derived"]["mac"] == "11:22:33:44:55:66"


@pytest.mark.skip(reason="broken, needs investigation")
@pytest.mark.asyncio
async def test_status_missing_required_key_in_json(airos6_device: AirOS6) -> None:
    """Test status() with a response missing a key required by the dataclass."""
    airos6_device.connected = True
    # Fixture is valid JSON, but is missing the entire 'wireless' block,
    # which is a required field for the AirOS6Data dataclass.
    invalid_data = {
        "host": {"hostname": "test"},
        "interfaces": [
            {"ifname": "br0", "hwaddr": "11:22:33:44:55:66", "enabled": True}
        ],
    }

    mock_status_response = MagicMock()
    mock_status_response.__aenter__.return_value = mock_status_response
    mock_status_response.text = AsyncMock(return_value=json.dumps(invalid_data))
    mock_status_response.status = 200

    with (
        patch.object(
            airos6_device.session, "request", return_value=mock_status_response
        ),
        patch("airos.airos6._LOGGER.exception") as mock_log_exception,
        pytest.raises(airos.exceptions.AirOSKeyDataMissingError) as excinfo,
    ):
        await airos6_device.status()

    # Check that the specific mashumaro error is logged and caught
    mock_log_exception.assert_called_once()
    assert "Failed to deserialize AirOS data" in mock_log_exception.call_args[0][0]
    # --- MODIFICATION START ---
    # Assert that the cause of our exception is the correct type from mashumaro
    assert isinstance(excinfo.value.__cause__, MissingField)
