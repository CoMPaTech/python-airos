"""Additional tests for airOS6 module."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from airos.airos6 import AirOS6
import airos.exceptions


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


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "method",
    ["download", "install", "progress", "discard", "firmware_staged", "warnings"],
)
async def test_firmware_methods_not_supported(
    airos6_device: AirOS6, method: str
) -> None:
    """Test firmware related methods raise not supported on AirOS6."""
    with pytest.raises(airos.exceptions.AirOSNotSupportedError):
        await getattr(airos6_device, method)()
