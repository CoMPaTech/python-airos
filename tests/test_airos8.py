"""Additional tests for airOS8 module."""

from http.cookies import SimpleCookie
import json
from unittest.mock import AsyncMock, MagicMock, patch

import aiofiles
import aiohttp
from mashumaro.exceptions import MissingField
import pytest

from airos.airos8 import AirOS8
import airos.base
import airos.exceptions


@pytest.mark.skip(reason="broken, needs investigation")
@pytest.mark.asyncio
async def test_login_no_csrf_token(airos8_device: AirOS8) -> None:
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
        airos8_device.session, "request", return_value=mock_login_response
    ):
        # We expect a return of None as the CSRF token is missing
        await airos8_device.login()


@pytest.mark.asyncio
async def test_login_connection_error(airos8_device: AirOS8) -> None:
    """Test aiohttp ClientError during login attempt."""
    with (
        patch.object(airos8_device.session, "request", side_effect=aiohttp.ClientError),
        pytest.raises(airos.exceptions.AirOSDeviceConnectionError),
    ):
        await airos8_device.login()


# --- Tests for status() and derived_data() logic ---
@pytest.mark.asyncio
async def test_status_when_not_connected(airos8_device: AirOS8) -> None:
    """Test calling status() before a successful login."""
    airos8_device.connected = False  # Ensure connected state is false
    with pytest.raises(airos.exceptions.AirOSDeviceConnectionError):
        await airos8_device.status()


# pylint: disable=pointless-string-statement
'''
@pytest.mark.asyncio
async def test_status_non_200_response(airos8_device: AirOS8) -> None:
    """Test status() with a non-successful HTTP response."""
    airos8_device.connected = True
    mock_status_response = MagicMock()
    mock_status_response.__aenter__.return_value = mock_status_response
    mock_status_response.text = AsyncMock(return_value="Error")
    mock_status_response.status = 500  # Simulate server error

    with (
        patch.object(airos8_device.session, "request", return_value=mock_status_response),
        pytest.raises(airos.exceptions.AirOSDeviceConnectionError),
    ):
        await airos8_device.status()
'''


@pytest.mark.asyncio
async def test_status_invalid_json_response(airos8_device: AirOS8) -> None:
    """Test status() with a response that is not valid JSON."""
    airos8_device.connected = True
    mock_status_response = MagicMock()
    mock_status_response.__aenter__.return_value = mock_status_response
    mock_status_response.text = AsyncMock(return_value="This is not JSON")
    mock_status_response.status = 200

    with (
        patch.object(
            airos8_device.session, "request", return_value=mock_status_response
        ),
        pytest.raises(airos.exceptions.AirOSDataMissingError),
    ):
        await airos8_device.status()


@pytest.mark.asyncio
async def test_status_missing_interface_key_data(airos8_device: AirOS8) -> None:
    """Test status() with a response missing critical data fields."""
    airos8_device.connected = True
    # The derived_data() function is called with a mocked response
    mock_status_response = MagicMock()
    mock_status_response.__aenter__.return_value = mock_status_response
    mock_status_response.text = AsyncMock(
        return_value=json.dumps({"system": {}})
    )  # Missing 'interfaces'
    mock_status_response.status = 200

    with (
        patch.object(
            airos8_device.session, "request", return_value=mock_status_response
        ),
        pytest.raises(airos.exceptions.AirOSKeyDataMissingError),
    ):
        await airos8_device.status()


@pytest.mark.asyncio
async def test_derived_data_no_interfaces_key(airos8_device: AirOS8) -> None:
    """Test derived_data() with a response that has no 'interfaces' key."""
    # This will directly test the 'if not interfaces:' branch (line 206)
    with pytest.raises(airos.exceptions.AirOSKeyDataMissingError):
        airos8_device.derived_data({})


@pytest.mark.asyncio
async def test_derived_data_no_br0_eth0_ath0(airos8_device: AirOS8) -> None:
    """Test derived_data() with an unexpected interface list, to test the fallback logic."""
    fixture_data = {
        "host": {
            "fwversion": "v8.0.0",
        },
        "interfaces": [
            {"ifname": "wan0", "enabled": True, "hwaddr": "11:22:33:44:55:66"}
        ],
    }

    adjusted_data = airos8_device.derived_data(fixture_data)
    assert adjusted_data["derived"]["mac_interface"] == "wan0"
    assert adjusted_data["derived"]["mac"] == "11:22:33:44:55:66"


# --- Tests for stakick() ---
@pytest.mark.asyncio
async def test_stakick_when_not_connected(airos8_device: AirOS8) -> None:
    """Test stakick() before a successful login."""
    airos8_device.connected = False
    with pytest.raises(airos.exceptions.AirOSDeviceConnectionError):
        await airos8_device.stakick("01:23:45:67:89:aB")


@pytest.mark.asyncio
async def test_stakick_no_mac_address(airos8_device: AirOS8) -> None:
    """Test stakick() with a None mac_address."""
    airos8_device.connected = True
    with pytest.raises(airos.exceptions.AirOSDataMissingError):
        await airos8_device.stakick(None)


@pytest.mark.skip(reason="broken, needs investigation")
@pytest.mark.asyncio
async def test_stakick_non_200_response(airos8_device: AirOS8) -> None:
    """Test stakick() with a non-successful HTTP response."""
    airos8_device.connected = True
    mock_stakick_response = MagicMock()
    mock_stakick_response.__aenter__.return_value = mock_stakick_response
    mock_stakick_response.text = AsyncMock(return_value="Error")
    mock_stakick_response.status = 500

    with patch.object(
        airos8_device.session, "request", return_value=mock_stakick_response
    ):
        assert not await airos8_device.stakick("01:23:45:67:89:aB")


@pytest.mark.asyncio
async def test_stakick_connection_error(airos8_device: AirOS8) -> None:
    """Test aiohttp ClientError during stakick."""
    airos8_device.connected = True
    with (
        patch.object(airos8_device.session, "request", side_effect=aiohttp.ClientError),
        pytest.raises(airos.exceptions.AirOSDeviceConnectionError),
    ):
        await airos8_device.stakick("01:23:45:67:89:aB")


# --- Tests for provmode() (Complete Coverage) ---
@pytest.mark.asyncio
async def test_provmode_when_not_connected(airos8_device: AirOS8) -> None:
    """Test provmode() before a successful login."""
    airos8_device.connected = False
    with pytest.raises(airos.exceptions.AirOSDeviceConnectionError):
        await airos8_device.provmode(active=True)


@pytest.mark.skip(reason="broken, needs investigation")
@pytest.mark.asyncio
async def test_provmode_activate_success(airos8_device: AirOS8) -> None:
    """Test successful activation of provisioning mode."""
    airos8_device.connected = True
    mock_provmode_response = MagicMock()
    mock_provmode_response.__aenter__.return_value = mock_provmode_response
    mock_provmode_response.status = 200
    mock_provmode_response.text = AsyncMock()
    mock_provmode_response.text.return_value = ""

    with patch.object(
        airos8_device.session, "request", return_value=mock_provmode_response
    ):
        assert await airos8_device.provmode(active=True)


@pytest.mark.skip(reason="broken, needs investigation")
@pytest.mark.asyncio
async def test_provmode_deactivate_success(airos8_device: AirOS8) -> None:
    """Test successful deactivation of provisioning mode."""
    airos8_device.connected = True
    mock_provmode_response = MagicMock()
    mock_provmode_response.__aenter__.return_value = mock_provmode_response
    mock_provmode_response.status = 200
    mock_provmode_response.text = AsyncMock()
    mock_provmode_response.text.return_value = ""

    with patch.object(
        airos8_device.session, "request", return_value=mock_provmode_response
    ):
        assert await airos8_device.provmode(active=False)


@pytest.mark.skip(reason="broken, needs investigation")
@pytest.mark.asyncio
async def test_provmode_non_200_response(airos8_device: AirOS8) -> None:
    """Test provmode() with a non-successful HTTP response."""
    airos8_device.connected = True
    mock_provmode_response = MagicMock()
    mock_provmode_response.__aenter__.return_value = mock_provmode_response
    mock_provmode_response.text = AsyncMock(return_value="Error")
    mock_provmode_response.status = 500

    with patch.object(
        airos8_device.session, "request", return_value=mock_provmode_response
    ):
        assert not await airos8_device.provmode(active=True)


@pytest.mark.asyncio
async def test_provmode_connection_error(airos8_device: AirOS8) -> None:
    """Test aiohttp ClientError during provmode."""
    airos8_device.connected = True
    with (
        patch.object(airos8_device.session, "request", side_effect=aiohttp.ClientError),
        pytest.raises(airos.exceptions.AirOSDeviceConnectionError),
    ):
        await airos8_device.provmode(active=True)


@pytest.mark.asyncio
async def test_status_missing_required_key_in_json(airos8_device: AirOS8) -> None:
    """Test status() with a response missing a key required by the dataclass."""
    airos8_device.connected = True
    # Fixture is valid JSON, but is missing the entire 'wireless' block,
    # which is a required field for the AirOS8Data dataclass.
    invalid_data = {
        "host": {"hostname": "test", "fwversion": "v8.0.0"},
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
            airos8_device.session, "request", return_value=mock_status_response
        ),
        patch("airos.base._LOGGER.exception") as mock_log_exception,
        pytest.raises(airos.exceptions.AirOSKeyDataMissingError) as excinfo,
    ):
        await airos8_device.status()

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
    airos8_device = AirOS8(
        host="http://192.168.1.3",
        username="test",
        password="test",
        session=mock_session,
    )
    airos8_device.connected = True

    mock_response = MagicMock()
    mock_response.__aenter__.return_value = mock_response
    mock_response.status = 200
    async with aiofiles.open("fixtures/warnings.json") as f:
        content = await f.read()
        mock_response_data = json.loads(content)
    mock_response.text = AsyncMock(return_value=json.dumps(mock_response_data))

    with patch.object(airos8_device.session, "request", return_value=mock_response):
        result = await airos8_device.warnings()
        assert result["isDefaultPasswd"] is False
        assert result["chAvailable"] is False


@pytest.mark.asyncio
async def test_warnings_raises_exception_on_invalid_json() -> None:
    """Test that warnings() raises an exception on invalid JSON response."""
    mock_session = MagicMock()
    airos8_device = AirOS8(
        host="http://192.168.1.3",
        username="test",
        password="test",
        session=mock_session,
    )
    airos8_device.connected = True

    mock_response = MagicMock()
    mock_response.__aenter__.return_value = mock_response
    mock_response.status = 200
    mock_response.text = AsyncMock(return_value="This is not JSON")

    with (
        patch.object(airos8_device.session, "request", return_value=mock_response),
        pytest.raises(airos.exceptions.AirOSDataMissingError),
    ):
        await airos8_device.warnings()


@pytest.mark.asyncio
async def test_update_check_correctly_parses_json() -> None:
    """Test that update_check() method correctly parses a valid JSON response."""
    mock_session = MagicMock()
    airos8_device = AirOS8(
        host="http://192.168.1.3",
        username="test",
        password="test",
        session=mock_session,
    )
    airos8_device.connected = True
    airos8_device.current_csrf_token = "mock-csrf-token"

    mock_response = MagicMock()
    mock_response.__aenter__.return_value = mock_response
    mock_response.status = 200
    async with aiofiles.open("fixtures/update_check_available.json") as f:
        content = await f.read()
        mock_response_data = json.loads(content)
    mock_response.text = AsyncMock(return_value=json.dumps(mock_response_data))

    with patch.object(airos8_device.session, "request", return_value=mock_response):
        result = await airos8_device.update_check()
        assert result["version"] == "v8.7.19"
        assert result["update"] is True


@pytest.mark.asyncio
async def test_update_check_raises_exception_on_invalid_json() -> None:
    """Test that update_check() raises an exception on invalid JSON response."""
    mock_session = MagicMock()
    airos8_device = AirOS8(
        host="http://192.168.1.3",
        username="test",
        password="test",
        session=mock_session,
    )
    airos8_device.connected = True
    airos8_device.current_csrf_token = "mock-csrf-token"

    mock_response = MagicMock()
    mock_response.__aenter__.return_value = mock_response
    mock_response.status = 200
    mock_response.text = AsyncMock(return_value="This is not JSON")

    with (
        patch.object(airos8_device.session, "request", return_value=mock_response),
        pytest.raises(airos.exceptions.AirOSDataMissingError),
    ):
        await airos8_device.update_check()


@pytest.mark.asyncio
async def test_warnings_when_not_connected() -> None:
    """Test calling warnings() before a successful login."""
    mock_session = MagicMock()
    airos8_device = AirOS8(
        host="http://192.168.1.3",
        username="test",
        password="test",
        session=mock_session,
    )
    airos8_device.connected = False  # Explicitly set connected state to false

    with pytest.raises(airos.exceptions.AirOSDeviceConnectionError):
        await airos8_device.warnings()


@pytest.mark.asyncio
async def test_update_check_when_not_connected() -> None:
    """Test calling update_check() before a successful login."""
    mock_session = MagicMock()
    airos8_device = AirOS8(
        host="http://192.168.1.3",
        username="test",
        password="test",
        session=mock_session,
    )
    airos8_device.connected = False  # Explicitly set connected state to false

    with pytest.raises(airos.exceptions.AirOSDeviceConnectionError):
        await airos8_device.update_check()


# --- Tests for firmware download/install ---
def _fw_device() -> AirOS8:
    """Return a connected AirOS8 device with a mocked session."""
    device = AirOS8(
        host="http://192.168.1.3",
        username="test",
        password="test",
        session=MagicMock(),
    )
    device.connected = True
    return device


async def _fw_response(
    fixture: str | None = None, text: str | None = None
) -> MagicMock:
    """Build a mocked aiohttp response from a fixture file or raw text."""
    if fixture is not None:
        async with aiofiles.open(f"fixtures/{fixture}") as f:
            text = await f.read()
    mock_response = MagicMock()
    mock_response.__aenter__.return_value = mock_response
    mock_response.status = 200
    mock_response.text = AsyncMock(return_value=text)
    return mock_response


@pytest.mark.asyncio
async def test_download_success_uses_long_timeout() -> None:
    """Test download() returns on ok and waits long enough for the device."""
    device = _fw_device()
    response = await _fw_response("fw_download_ok.json")
    with patch.object(device.session, "request", return_value=response) as req:
        result = await device.download()
    assert result == {"ok": True}
    timeout = req.call_args.kwargs["timeout"]
    assert timeout.total == airos.base.FIRMWARE_DOWNLOAD_TIMEOUT


@pytest.mark.asyncio
async def test_download_failure_raises() -> None:
    """Test download() raises when the device reports a failed download."""
    device = _fw_device()
    response = await _fw_response("fw_download_failed.json")
    with (
        patch.object(device.session, "request", return_value=response),
        pytest.raises(
            airos.exceptions.AirOSFirmwareDownloadError,
            match=r"Firmware download failed\. \(unknown error\)",
        ),
    ):
        await device.download()


@pytest.mark.asyncio
async def test_download_unexpected_response_raises() -> None:
    """Test download() raises when the response has no ok flag."""
    device = _fw_device()
    response = await _fw_response(text="[]")
    with (
        patch.object(device.session, "request", return_value=response),
        pytest.raises(airos.exceptions.AirOSFirmwareDownloadError),
    ):
        await device.download()


@pytest.mark.asyncio
async def test_install_success() -> None:
    """Test install() returns when the device accepts the update."""
    device = _fw_device()
    response = await _fw_response("fw_install_ok.json")
    with patch.object(device.session, "request", return_value=response) as req:
        result = await device.install()
    assert result["code"] == 0
    assert req.call_args.kwargs["json"] == {"do_update": 1}


@pytest.mark.asyncio
async def test_install_with_password() -> None:
    """Test install() passes the password when required by the device."""
    device = _fw_device()
    response = await _fw_response("fw_install_ok.json")
    with patch.object(device.session, "request", return_value=response) as req:
        await device.install(password="secret")
    assert req.call_args.kwargs["json"] == {"do_update": 1, "password": "secret"}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("text", "match"),
    [
        ('{"code": 1, "message": "No firmware uploaded"}', "No firmware uploaded"),
        ('{"code": 1}', "unknown error"),
        ("[]", "unknown error"),
    ],
)
async def test_install_failure_raises(text: str, match: str) -> None:
    """Test install() raises when the device refuses the update."""
    device = _fw_device()
    response = await _fw_response(text=text)
    with (
        patch.object(device.session, "request", return_value=response),
        pytest.raises(airos.exceptions.AirOSFirmwareInstallError, match=match),
    ):
        await device.install()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("fixture", "uploaded", "version"),
    [
        ("warnings_fw_staged.json", True, "WA.v8.7.25"),
        ("warnings.json", False, ""),
    ],
)
async def test_firmware_staged(fixture: str, uploaded: bool, version: str) -> None:
    """Test firmware_staged() reports the staged image from warnings."""
    device = _fw_device()
    response = await _fw_response(fixture)
    with patch.object(device.session, "request", return_value=response):
        result = await device.firmware_staged()
    assert result["uploaded"] is uploaded
    assert result["version"] == version


@pytest.mark.asyncio
async def test_firmware_staged_missing_key() -> None:
    """Test firmware_staged() returns empty dict on older warnings payloads."""
    device = _fw_device()
    response = await _fw_response(text='{"isDefaultPasswd": false}')
    with patch.object(device.session, "request", return_value=response):
        assert await device.firmware_staged() == {}


@pytest.mark.asyncio
@pytest.mark.parametrize("text", ["[]", '{"firmware": [1]}', '{"firmware": "x"}'])
async def test_firmware_staged_malformed_raises(text: str) -> None:
    """Test firmware_staged() raises on malformed warnings payloads."""
    device = _fw_device()
    response = await _fw_response(text=text)
    with (
        patch.object(device.session, "request", return_value=response),
        pytest.raises(airos.exceptions.AirOSDataMissingError),
    ):
        await device.firmware_staged()


@pytest.mark.asyncio
async def test_discard() -> None:
    """Test discard() posts the form and reports success."""
    device = _fw_device()
    response = await _fw_response("fw_download_ok.json")
    with patch.object(device.session, "request", return_value=response) as req:
        assert await device.discard() is True
    assert req.call_args.kwargs["data"] == {"discard": 1}
