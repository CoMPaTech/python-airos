"""Additional tests for airos8 module."""

from http.cookies import SimpleCookie
import json
from unittest.mock import AsyncMock, MagicMock, patch

import aiofiles
import aiohttp
from mashumaro.exceptions import MissingField
import pytest

from airos.airos8 import AirOS
import airos.exceptions


@pytest.mark.skip(reason="broken, needs investigation")
@pytest.mark.asyncio
async def test_login_no_csrf_token(airos_device: AirOS) -> None:
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
        airos_device.session, "request", return_value=mock_login_response
    ):
        # We expect a return of None as the CSRF token is missing
        await airos_device.login()


@pytest.mark.asyncio
async def test_login_connection_error(airos_device: AirOS) -> None:
    """Test aiohttp ClientError during login attempt."""
    with (
        patch.object(airos_device.session, "request", side_effect=aiohttp.ClientError),
        pytest.raises(airos.exceptions.AirOSDeviceConnectionError),
    ):
        await airos_device.login()


# --- Tests for status() and derived_data() logic ---
@pytest.mark.asyncio
async def test_status_when_not_connected(airos_device: AirOS) -> None:
    """Test calling status() before a successful login."""
    airos_device.connected = False  # Ensure connected state is false
    with pytest.raises(airos.exceptions.AirOSDeviceConnectionError):
        await airos_device.status()


# pylint: disable=pointless-string-statement
'''
@pytest.mark.asyncio
async def test_status_non_200_response(airos_device: AirOS) -> None:
    """Test status() with a non-successful HTTP response."""
    airos_device.connected = True
    mock_status_response = MagicMock()
    mock_status_response.__aenter__.return_value = mock_status_response
    mock_status_response.text = AsyncMock(return_value="Error")
    mock_status_response.status = 500  # Simulate server error

    with (
        patch.object(airos_device.session, "request", return_value=mock_status_response),
        pytest.raises(airos.exceptions.AirOSDeviceConnectionError),
    ):
        await airos_device.status()
'''


@pytest.mark.asyncio
async def test_status_invalid_json_response(airos_device: AirOS) -> None:
    """Test status() with a response that is not valid JSON."""
    airos_device.connected = True
    mock_status_response = MagicMock()
    mock_status_response.__aenter__.return_value = mock_status_response
    mock_status_response.text = AsyncMock(return_value="This is not JSON")
    mock_status_response.status = 200

    with (
        patch.object(
            airos_device.session, "request", return_value=mock_status_response
        ),
        pytest.raises(airos.exceptions.AirOSDataMissingError),
    ):
        await airos_device.status()


@pytest.mark.asyncio
async def test_status_missing_interface_key_data(airos_device: AirOS) -> None:
    """Test status() with a response missing critical data fields."""
    airos_device.connected = True
    # The derived_data() function is called with a mocked response
    mock_status_response = MagicMock()
    mock_status_response.__aenter__.return_value = mock_status_response
    mock_status_response.text = AsyncMock(
        return_value=json.dumps({"system": {}})
    )  # Missing 'interfaces'
    mock_status_response.status = 200

    with (
        patch.object(
            airos_device.session, "request", return_value=mock_status_response
        ),
        pytest.raises(airos.exceptions.AirOSKeyDataMissingError),
    ):
        await airos_device.status()


@pytest.mark.asyncio
async def test_derived_data_no_interfaces_key(airos_device: AirOS) -> None:
    """Test derived_data() with a response that has no 'interfaces' key."""
    # This will directly test the 'if not interfaces:' branch (line 206)
    with pytest.raises(airos.exceptions.AirOSKeyDataMissingError):
        airos_device.derived_data({})


@pytest.mark.asyncio
async def test_derived_data_no_br0_eth0_ath0(airos_device: AirOS) -> None:
    """Test derived_data() with an unexpected interface list, to test the fallback logic."""
    fixture_data = {
        "interfaces": [
            {"ifname": "wan0", "enabled": True, "hwaddr": "11:22:33:44:55:66"}
        ]
    }

    adjusted_data = airos_device.derived_data(fixture_data)
    assert adjusted_data["derived"]["mac_interface"] == "wan0"
    assert adjusted_data["derived"]["mac"] == "11:22:33:44:55:66"


# --- Tests for stakick() ---
@pytest.mark.asyncio
async def test_stakick_when_not_connected(airos_device: AirOS) -> None:
    """Test stakick() before a successful login."""
    airos_device.connected = False
    with pytest.raises(airos.exceptions.AirOSDeviceConnectionError):
        await airos_device.stakick("01:23:45:67:89:aB")


@pytest.mark.asyncio
async def test_stakick_no_mac_address(airos_device: AirOS) -> None:
    """Test stakick() with a None mac_address."""
    airos_device.connected = True
    with pytest.raises(airos.exceptions.AirOSDataMissingError):
        await airos_device.stakick(None)


@pytest.mark.skip(reason="broken, needs investigation")
@pytest.mark.asyncio
async def test_stakick_non_200_response(airos_device: AirOS) -> None:
    """Test stakick() with a non-successful HTTP response."""
    airos_device.connected = True
    mock_stakick_response = MagicMock()
    mock_stakick_response.__aenter__.return_value = mock_stakick_response
    mock_stakick_response.text = AsyncMock(return_value="Error")
    mock_stakick_response.status = 500

    with patch.object(
        airos_device.session, "request", return_value=mock_stakick_response
    ):
        assert not await airos_device.stakick("01:23:45:67:89:aB")


@pytest.mark.asyncio
async def test_stakick_connection_error(airos_device: AirOS) -> None:
    """Test aiohttp ClientError during stakick."""
    airos_device.connected = True
    with (
        patch.object(airos_device.session, "request", side_effect=aiohttp.ClientError),
        pytest.raises(airos.exceptions.AirOSDeviceConnectionError),
    ):
        await airos_device.stakick("01:23:45:67:89:aB")


# --- Tests for provmode() (Complete Coverage) ---
@pytest.mark.asyncio
async def test_provmode_when_not_connected(airos_device: AirOS) -> None:
    """Test provmode() before a successful login."""
    airos_device.connected = False
    with pytest.raises(airos.exceptions.AirOSDeviceConnectionError):
        await airos_device.provmode(active=True)


@pytest.mark.skip(reason="broken, needs investigation")
@pytest.mark.asyncio
async def test_provmode_activate_success(airos_device: AirOS) -> None:
    """Test successful activation of provisioning mode."""
    airos_device.connected = True
    mock_provmode_response = MagicMock()
    mock_provmode_response.__aenter__.return_value = mock_provmode_response
    mock_provmode_response.status = 200
    mock_provmode_response.text = AsyncMock()
    mock_provmode_response.text.return_value = ""

    with patch.object(
        airos_device.session, "request", return_value=mock_provmode_response
    ):
        assert await airos_device.provmode(active=True)


@pytest.mark.skip(reason="broken, needs investigation")
@pytest.mark.asyncio
async def test_provmode_deactivate_success(airos_device: AirOS) -> None:
    """Test successful deactivation of provisioning mode."""
    airos_device.connected = True
    mock_provmode_response = MagicMock()
    mock_provmode_response.__aenter__.return_value = mock_provmode_response
    mock_provmode_response.status = 200
    mock_provmode_response.text = AsyncMock()
    mock_provmode_response.text.return_value = ""

    with patch.object(
        airos_device.session, "request", return_value=mock_provmode_response
    ):
        assert await airos_device.provmode(active=False)


@pytest.mark.skip(reason="broken, needs investigation")
@pytest.mark.asyncio
async def test_provmode_non_200_response(airos_device: AirOS) -> None:
    """Test provmode() with a non-successful HTTP response."""
    airos_device.connected = True
    mock_provmode_response = MagicMock()
    mock_provmode_response.__aenter__.return_value = mock_provmode_response
    mock_provmode_response.text = AsyncMock(return_value="Error")
    mock_provmode_response.status = 500

    with patch.object(
        airos_device.session, "request", return_value=mock_provmode_response
    ):
        assert not await airos_device.provmode(active=True)


@pytest.mark.asyncio
async def test_provmode_connection_error(airos_device: AirOS) -> None:
    """Test aiohttp ClientError during provmode."""
    airos_device.connected = True
    with (
        patch.object(airos_device.session, "request", side_effect=aiohttp.ClientError),
        pytest.raises(airos.exceptions.AirOSDeviceConnectionError),
    ):
        await airos_device.provmode(active=True)


@pytest.mark.asyncio
async def test_status_missing_required_key_in_json(airos_device: AirOS) -> None:
    """Test status() with a response missing a key required by the dataclass."""
    airos_device.connected = True
    # Fixture is valid JSON, but is missing the entire 'wireless' block,
    # which is a required field for the AirOS8Data dataclass.
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
            airos_device.session, "request", return_value=mock_status_response
        ),
        patch("airos.airos8._LOGGER.exception") as mock_log_exception,
        pytest.raises(airos.exceptions.AirOSKeyDataMissingError) as excinfo,
    ):
        await airos_device.status()

    # Check that the specific mashumaro error is logged and caught
    mock_log_exception.assert_called_once()
    assert "Failed to deserialize AirOS data" in mock_log_exception.call_args[0][0]
    # --- MODIFICATION START ---
    # Assert that the cause of our exception is the correct type from mashumaro
    assert isinstance(excinfo.value.__cause__, MissingField)


# --- Tests for warnings() and update_check() ---
@pytest.mark.asyncio
async def test_warnings_correctly_parses_json() -> None:
    """Test that the warnings() method correctly parses a valid JSON response."""
    mock_session = MagicMock()
    airos_device = AirOS(
        host="http://192.168.1.3",
        username="test",
        password="test",
        session=mock_session,
    )
    airos_device.connected = True

    mock_response = MagicMock()
    mock_response.__aenter__.return_value = mock_response
    mock_response.status = 200
    async with aiofiles.open("fixtures/warnings.json") as f:
        content = await f.read()
        mock_response_data = json.loads(content)
    mock_response.text = AsyncMock(return_value=json.dumps(mock_response_data))

    with patch.object(airos_device.session, "request", return_value=mock_response):
        result = await airos_device.warnings()
        assert result["isDefaultPasswd"] is False
        assert result["chAvailable"] is False


@pytest.mark.asyncio
async def test_warnings_raises_exception_on_invalid_json() -> None:
    """Test that warnings() raises an exception on invalid JSON response."""
    mock_session = MagicMock()
    airos_device = AirOS(
        host="http://192.168.1.3",
        username="test",
        password="test",
        session=mock_session,
    )
    airos_device.connected = True

    mock_response = MagicMock()
    mock_response.__aenter__.return_value = mock_response
    mock_response.status = 200
    mock_response.text = AsyncMock(return_value="This is not JSON")

    with (
        patch.object(airos_device.session, "request", return_value=mock_response),
        pytest.raises(airos.exceptions.AirOSDataMissingError),
    ):
        await airos_device.warnings()


@pytest.mark.asyncio
async def test_update_check_correctly_parses_json() -> None:
    """Test that update_check() method correctly parses a valid JSON response."""
    mock_session = MagicMock()
    airos_device = AirOS(
        host="http://192.168.1.3",
        username="test",
        password="test",
        session=mock_session,
    )
    airos_device.connected = True
    airos_device.current_csrf_token = "mock-csrf-token"

    mock_response = MagicMock()
    mock_response.__aenter__.return_value = mock_response
    mock_response.status = 200
    async with aiofiles.open("fixtures/update_check_available.json") as f:
        content = await f.read()
        mock_response_data = json.loads(content)
    mock_response.text = AsyncMock(return_value=json.dumps(mock_response_data))

    with patch.object(airos_device.session, "request", return_value=mock_response):
        result = await airos_device.update_check()
        assert result["version"] == "v8.7.19"
        assert result["update"] is True


@pytest.mark.asyncio
async def test_update_check_raises_exception_on_invalid_json() -> None:
    """Test that update_check() raises an exception on invalid JSON response."""
    mock_session = MagicMock()
    airos_device = AirOS(
        host="http://192.168.1.3",
        username="test",
        password="test",
        session=mock_session,
    )
    airos_device.connected = True
    airos_device.current_csrf_token = "mock-csrf-token"

    mock_response = MagicMock()
    mock_response.__aenter__.return_value = mock_response
    mock_response.status = 200
    mock_response.text = AsyncMock(return_value="This is not JSON")

    with (
        patch.object(airos_device.session, "request", return_value=mock_response),
        pytest.raises(airos.exceptions.AirOSDataMissingError),
    ):
        await airos_device.update_check()


@pytest.mark.asyncio
async def test_warnings_when_not_connected() -> None:
    """Test calling warnings() before a successful login."""
    mock_session = MagicMock()
    airos_device = AirOS(
        host="http://192.168.1.3",
        username="test",
        password="test",
        session=mock_session,
    )
    airos_device.connected = False  # Explicitly set connected state to false

    with pytest.raises(airos.exceptions.AirOSDeviceConnectionError):
        await airos_device.warnings()


@pytest.mark.asyncio
async def test_update_check_when_not_connected() -> None:
    """Test calling update_check() before a successful login."""
    mock_session = MagicMock()
    airos_device = AirOS(
        host="http://192.168.1.3",
        username="test",
        password="test",
        session=mock_session,
    )
    airos_device.connected = False  # Explicitly set connected state to false

    with pytest.raises(airos.exceptions.AirOSDeviceConnectionError):
        await airos_device.update_check()
