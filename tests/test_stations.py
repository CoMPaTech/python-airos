"""Ubiquiti AirOS tests."""

from http.cookies import SimpleCookie
import json
import os
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import aiofiles
from mashumaro.exceptions import MissingField
import pytest

from airos.airos8 import AirOS
from airos.data import AirOS8Data as AirOSData, Wireless
from airos.exceptions import AirOSDeviceConnectionError, AirOSKeyDataMissingError


async def _read_fixture(fixture: str = "loco5ac_ap-ptp") -> Any:
    """Read fixture file per device type."""
    fixture_dir = os.path.join(os.path.dirname(__file__), "..", "fixtures", "userdata")
    path = os.path.join(fixture_dir, f"{fixture}.json")
    try:
        async with aiofiles.open(path, encoding="utf-8") as f:
            return json.loads(await f.read())
    except FileNotFoundError:
        pytest.fail(f"Fixture file not found: {path}")
    except json.JSONDecodeError as e:
        pytest.fail(f"Invalid JSON in fixture file {path}: {e}")


@pytest.mark.skip(reason="broken, needs investigation")
@patch("airos.airos8._LOGGER")
@pytest.mark.asyncio
async def test_status_logs_redacted_data_on_invalid_value(
    mock_logger: MagicMock, airos_device: AirOS
) -> None:
    """Test that the status method correctly logs redacted data when it encounters an InvalidFieldValue during deserialization."""
    # --- Prepare fake POST /api/auth response with cookies ---
    cookie = SimpleCookie()
    cookie["session_id"] = "test-cookie"
    cookie["AIROS_TOKEN"] = "abc123"
    mock_login_response = MagicMock()
    mock_login_response.__aenter__.return_value = mock_login_response
    mock_login_response.text = AsyncMock(return_value="{}")
    mock_login_response.status = 200
    mock_login_response.cookies = cookie
    mock_login_response.headers = {"X-CSRF-ID": "test-csrf-token"}

    # --- Prepare a response with data that would be redacted ---
    fixture_data = await _read_fixture("mocked_invalid_wireless_mode")
    mock_status_response = MagicMock()
    mock_status_response.__aenter__.return_value = mock_status_response
    mock_status_response.text = AsyncMock(return_value=json.dumps(fixture_data))
    mock_status_response.status = 200
    mock_status_response.json = AsyncMock(return_value=fixture_data)

    # --- Patch `from_dict` to force the desired exception ---
    # We use a valid fixture response, but force the exception to be a MissingField
    with (
        patch.object(airos_device.session, "post", return_value=mock_login_response),
        patch.object(airos_device.session, "get", return_value=mock_status_response),
        patch(
            "airos.airos8.AirOSData.from_dict",
            side_effect=MissingField(
                field_name="wireless", field_type=Wireless, holder_class=AirOSData
            ),
        ),
    ):
        await airos_device.login()
        with pytest.raises(AirOSKeyDataMissingError):
            await airos_device.status()

    # --- Assertions for the logging and redaction ---
    assert mock_logger.exception.called
    assert mock_logger.exception.call_count == 1
    assert mock_logger.error.called is False

    # Get the dictionary that was passed as the second argument to the logger
    logged_data = mock_logger.exception.call_args[0][1]

    # Assert that the dictionary has been redacted
    assert "wireless" in logged_data
    assert "essid" in logged_data["wireless"]
    assert logged_data["wireless"]["essid"] == "REDACTED"
    assert "host" in logged_data
    assert "hostname" in logged_data["host"]
    assert logged_data["host"]["hostname"] == "REDACTED"
    assert "apmac" in logged_data["wireless"]
    assert logged_data["wireless"]["apmac"] == "00:11:22:33:89:AB"
    assert "interfaces" in logged_data
    assert len(logged_data["interfaces"]) > 2
    assert "status" in logged_data["interfaces"][2]
    assert "ipaddr" in logged_data["interfaces"][2]["status"]
    assert logged_data["interfaces"][2]["status"]["ipaddr"] == "127.0.0.3"


@pytest.mark.skip(reason="broken, needs investigation")
@patch("airos.airos8._LOGGER")
@pytest.mark.asyncio
async def test_status_logs_exception_on_missing_field(
    mock_logger: MagicMock, airos_device: AirOS
) -> None:
    """Test that the status method correctly logs a full exception when it encounters a MissingField during deserialization."""
    # --- Prepare fake POST /api/auth response with cookies ---
    cookie = SimpleCookie()
    cookie["session_id"] = "test-cookie"
    cookie["AIROS_TOKEN"] = "abc123"
    mock_login_response = MagicMock()
    mock_login_response.__aenter__.return_value = mock_login_response
    mock_login_response.text = AsyncMock(return_value="{}")
    mock_login_response.status = 200
    mock_login_response.cookies = cookie
    mock_login_response.headers = {"X-CSRF-ID": "test-csrf-token"}

    # --- Prepare fake GET /api/status response with the missing field fixture ---
    mock_status_response = MagicMock()
    mock_status_response.__aenter__.return_value = mock_status_response
    mock_status_response.status = 500  # Non-200 status
    mock_status_response.text = AsyncMock(return_value="Error")
    mock_status_response.json = AsyncMock(return_value={})

    with (
        patch.object(
            airos_device.session,
            "request",
            side_effect=[mock_login_response, mock_status_response],
        ),
    ):
        await airos_device.login()
        with pytest.raises(AirOSDeviceConnectionError):
            await airos_device.status()

    # Assert the logger was called correctly
    assert mock_logger.error.called
    assert mock_logger.error.call_count == 1

    log_args = mock_logger.error.call_args[0]
    assert log_args[0] == "API call to %s failed with status %d: %s"
    assert log_args[2] == 500
    assert log_args[3] == "Error"


@pytest.mark.parametrize(
    ("mode", "fixture"),
    [
        ("ap-ptp", "loco5ac_ap-ptp"),
        ("ap-ptp", "nanostation_ap-ptp_8718_missing_gps"),
        ("sta-ptp", "loco5ac_sta-ptp"),
        ("sta-ptmp", "mocked_sta-ptmp"),
        ("ap-ptmp", "liteapgps_ap_ptmp_40mhz"),
        ("sta-ptmp", "nanobeam5ac_sta_ptmp_40mhz"),
    ],
)
@pytest.mark.asyncio
async def test_ap_object(
    airos_device: AirOS, base_url: str, mode: str, fixture: str
) -> None:
    """Test device operation using the new _request_json method."""
    fixture_data = await _read_fixture(fixture)

    # Create an async mock that can return different values for different calls
    mock_request_json = AsyncMock(
        side_effect=[
            {},  # First call for login()
            fixture_data,  # Second call for status()
        ]
    )

    with (
        # Patch the internal method, not the session object
        patch.object(airos_device, "_request_json", new=mock_request_json),
        # You need to manually set the connected state since login() is mocked
        patch.object(airos_device, "connected", True),
    ):
        # We don't need to patch the session directly anymore
        await airos_device.login()
        status: AirOSData = await airos_device.status()

    # Assertions remain the same as they check the final result
    assert status.wireless.mode
    assert status.wireless.mode.value == mode
    assert status.derived.mac_interface == "br0"

    cookie = SimpleCookie()
    cookie["session_id"] = "test-cookie"
    cookie["AIROS_TOKEN"] = "abc123"


@pytest.mark.skip(reason="broken, needs investigation")
@pytest.mark.asyncio
async def test_reconnect(airos_device: AirOS, base_url: str) -> None:
    """Test reconnect client."""
    # --- Prepare fake POST /api/stakick response ---
    mock_stakick_response = MagicMock()
    mock_stakick_response.__aenter__.return_value = mock_stakick_response
    mock_stakick_response.status = 200
    mock_stakick_response.text = AsyncMock()
    mock_stakick_response.text.return_value = ""

    with (
        patch.object(
            airos_device.session, "request", return_value=mock_stakick_response
        ),
        patch.object(airos_device, "connected", True),
    ):
        assert await airos_device.stakick("01:23:45:67:89:aB")
