"""HTTP flow tests against an in-process fake airOS device."""

from __future__ import annotations

from collections.abc import AsyncGenerator, Callable
from dataclasses import dataclass, field
import json
from pathlib import Path
from ssl import SSLError
from typing import Any
from unittest.mock import MagicMock, patch
from urllib.parse import parse_qsl

import aiohttp
from aiohttp import web
from mashumaro.exceptions import InvalidFieldValue, MissingField
import pytest

from airos.airos6 import AirOS6
from airos.airos8 import AirOS8
import airos.exceptions
from airos.helpers import async_get_firmware_data

# pylint: disable=redefined-outer-name

FIXTURES = Path(__file__).parent.parent / "fixtures"

Handler = Callable[[web.Request], web.StreamResponse]


def _fixture(name: str) -> Any:
    """Load a JSON fixture."""
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def reply(
    status: int = 200,
    payload: Any = None,
    body: str = "",
    headers: dict[str, str] | None = None,
) -> Handler:
    """Build a canned response handler."""

    def _handler(_request: web.Request) -> web.StreamResponse:
        text = json.dumps(payload) if payload is not None else body
        return web.Response(status=status, text=text, headers=headers)

    return _handler


def disconnect(request: web.Request) -> web.StreamResponse:
    """Drop the connection without answering."""
    assert request.transport is not None
    request.transport.close()
    return web.Response()


@dataclass
class Sent:
    """A request received by the fake device."""

    headers: dict[str, str]
    body: str

    @property
    def form(self) -> dict[str, str]:
        """Return the body decoded as a form."""
        return dict(parse_qsl(self.body))


@dataclass
class FakeDevice:
    """Minimal fake airOS HTTP endpoint."""

    url: str = ""
    socket_path: str = ""
    routes: dict[tuple[str, str], Handler] = field(default_factory=dict)
    sent: dict[tuple[str, str], list[Sent]] = field(default_factory=dict)

    def on(self, method: str, path: str, handler: Handler) -> None:
        """Register a handler for method + path."""
        self.routes[(method, path)] = handler

    def last(self, method: str, path: str) -> Sent:
        """Return the single request received on method + path."""
        calls = self.sent.get((method, path), [])
        assert len(calls) == 1, calls
        return calls[0]

    async def handle(self, request: web.Request) -> web.StreamResponse:
        """Dispatch an incoming request."""
        key = (request.method, request.path)
        self.sent.setdefault(key, []).append(
            Sent(dict(request.headers), await request.text())
        )
        handler = self.routes.get(key)
        if handler is None:
            return web.Response(status=404)
        return handler(request)


@pytest.fixture(autouse=True)
def _allow_local_sockets() -> None:
    """Undo pytest-socket restrictions (e.g. Home Assistant's test plugin).

    The fake device is served over a unix socket; pytest-socket (when
    installed) blocks connect() for anything but 127.0.0.1.
    """
    try:
        import pytest_socket  # noqa: PLC0415  # pylint: disable=import-outside-toplevel
    except ImportError:
        return
    pytest_socket.enable_socket()
    remove = getattr(pytest_socket, "_remove_restrictions", None)
    if remove is not None:
        remove()


@pytest.fixture
async def device(tmp_path: Path) -> AsyncGenerator[FakeDevice]:
    """Run a fake device on a unix socket (TCP may be blocked by pytest-socket)."""
    fake = FakeDevice(url="http://device.local", socket_path=str(tmp_path / "dev.sock"))
    app = web.Application()
    app.router.add_route("*", "/{tail:.*}", fake.handle)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.UnixSite(runner, fake.socket_path).start()
    yield fake
    await runner.cleanup()


@pytest.fixture
async def session(device: FakeDevice) -> AsyncGenerator[aiohttp.ClientSession]:
    """Client session routed to the fake device."""
    connector = aiohttp.UnixConnector(path=device.socket_path)
    async with aiohttp.ClientSession(connector=connector) as client:
        yield client


@pytest.fixture
def airos8(device: FakeDevice, session: aiohttp.ClientSession) -> AirOS8:
    """AirOS8 client pointed at the fake device."""
    return AirOS8(device.url, "user", "pass", session, use_ssl=False)


@pytest.fixture
def airos6(device: FakeDevice, session: aiohttp.ClientSession) -> AirOS6:
    """AirOS6 client pointed at the fake device."""
    return AirOS6(device.url, "user", "pass", session, use_ssl=False)


def _mock_v6_login(device: FakeDevice) -> None:
    """Register a successful v6 XM login sequence."""
    device.on(
        "GET",
        "/login.cgi",
        reply(headers={"Set-Cookie": "AIROS_SESSIONID=xyz; Path=/"}),
    )
    device.on("POST", "/login.cgi", reply(302, headers={"Location": "/index.cgi"}))
    device.on("GET", "/index.cgi", reply(body="ok"))


# --- Login (v8 /api/auth) ---
@pytest.mark.asyncio
async def test_login_no_csrf_token(airos8: AirOS8, device: FakeDevice) -> None:
    """Login succeeds and stores the auth cookie when no X-CSRF-ID is sent."""
    device.on(
        "POST", "/api/auth", reply(body="{}", headers={"Set-Cookie": "AIROS_TOKEN=abc"})
    )
    await airos8.login()

    assert airos8.connected is True
    assert airos8._csrf_id is None  # noqa: SLF001
    assert airos8._auth_cookie == "AIROS_TOKEN=abc"  # noqa: SLF001
    assert json.loads(device.last("POST", "/api/auth").body) == {
        "username": "user",
        "password": "pass",
    }


@pytest.mark.asyncio
async def test_login_stores_and_sends_auth_headers(
    airos8: AirOS8, device: FakeDevice
) -> None:
    """CSRF id and AIROS_ cookie from login are sent on authenticated calls."""
    device.on(
        "POST",
        "/api/auth",
        reply(
            payload={},
            headers={"X-CSRF-ID": "csrf123", "Set-Cookie": "AIROS_ABCDEF=tok"},
        ),
    )
    device.on("GET", "/api/warnings", reply(payload={"isDefaultPasswd": False}))
    await airos8.login()
    assert await airos8.warnings() == {"isDefaultPasswd": False}

    headers = device.last("GET", "/api/warnings").headers
    assert headers["X-CSRF-ID"] == "csrf123"
    assert headers["Cookie"] == "AIROS_ABCDEF=tok"


@pytest.mark.asyncio
async def test_login_invalid_credentials(airos8: AirOS8, device: FakeDevice) -> None:
    """A 401 on login maps to an authentication error."""
    device.on("POST", "/api/auth", reply(401))
    with pytest.raises(airos.exceptions.AirOSConnectionAuthenticationError):
        await airos8.login()
    assert airos8.connected is False


# --- Login fallback to v6 (/login.cgi) ---
@pytest.mark.asyncio
async def test_login_falls_back_to_v6(airos8: AirOS8, device: FakeDevice) -> None:
    """A 404 on /api/auth falls back to the v6 login flow."""
    _mock_v6_login(device)
    await airos8.login()

    assert airos8.connected is True
    assert airos8.api_version == 6
    assert airos8._auth_cookie == "AIROS_SESSIONID=xyz"  # noqa: SLF001
    assert device.last("POST", "/login.cgi").form == {
        "username": "user",
        "password": "pass",
        "uri": "/index.cgi",
    }


@pytest.mark.asyncio
async def test_login_v6_fallback_maps_connection_errors(
    airos8: AirOS8, device: FakeDevice
) -> None:
    """Transport errors in the v6 fallback raise library exceptions."""
    device.on("GET", "/login.cgi", disconnect)
    with pytest.raises(airos.exceptions.AirOSDeviceConnectionError):
        await airos8.login()


def _ssl_error(cause_message: str) -> aiohttp.ClientConnectorSSLError:
    """Build a ClientConnectorSSLError caused by an SSLError."""
    err = aiohttp.ClientConnectorSSLError(MagicMock(), OSError(1, "ssl"))
    err.__cause__ = SSLError(cause_message)
    return err


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("cause", "expected"),
    [
        (
            "[SSL: SSLV3_ALERT_HANDSHAKE_FAILURE] sslv3 alert handshake failure",
            airos.exceptions.AirOSTLSCompatibilityError,
        ),
        ("certificate verify failed", airos.exceptions.AirOSDeviceConnectionError),
    ],
)
async def test_login_v6_maps_ssl_errors(
    airos6: AirOS6, cause: str, expected: type[Exception]
) -> None:
    """SSL errors during v6 login map to TLS-compat or connection errors."""
    with (
        patch.object(airos6, "_login_v6_flow", side_effect=_ssl_error(cause)),
        pytest.raises(expected),
    ):
        await airos6._login_v6()  # noqa: SLF001


@pytest.mark.asyncio
async def test_login_v6_without_session_cookie(
    airos6: AirOS6, device: FakeDevice
) -> None:
    """v6 login fails when /login.cgi hands out no AIROS_ cookie."""
    device.on("GET", "/login.cgi", reply())
    with pytest.raises(airos.exceptions.AirOSDeviceConnectionError):
        await airos6.login()
    assert airos6.connected is False


@pytest.mark.asyncio
async def test_login_v6_wrong_credentials(airos6: AirOS6, device: FakeDevice) -> None:
    """v6 login fails when the form post does not redirect."""
    _mock_v6_login(device)
    device.on("POST", "/login.cgi", reply(200))
    with pytest.raises(airos.exceptions.AirOSConnectionAuthenticationError):
        await airos6.login()


@pytest.mark.asyncio
async def test_login_v6_session_not_activated(
    airos6: AirOS6, device: FakeDevice
) -> None:
    """v6 login fails when index.cgi bounces back to the login page."""
    _mock_v6_login(device)
    device.on("GET", "/index.cgi", reply(302, headers={"Location": "/login.cgi"}))
    with pytest.raises(airos.exceptions.AirOSConnectionAuthenticationError):
        await airos6.login()


# --- status() ---
@pytest.mark.asyncio
async def test_status_missing_required_key_v6(
    airos6: AirOS6, device: FakeDevice
) -> None:
    """status() maps a missing dataclass field to AirOSKeyDataMissingError."""
    airos6.connected = True
    device.on(
        "GET",
        "/status.cgi",
        reply(
            payload={
                "host": {"hostname": "test", "fwversion": "v6.3.16"},
                "interfaces": [
                    {"ifname": "br0", "hwaddr": "11:22:33:44:55:66", "enabled": True}
                ],
            }
        ),
    )
    with (
        patch("airos.base._LOGGER.exception") as mock_log_exception,
        pytest.raises(airos.exceptions.AirOSKeyDataMissingError) as excinfo,
    ):
        await airos6.status()

    mock_log_exception.assert_called_once()
    assert "Failed to deserialize AirOS data" in mock_log_exception.call_args[0][0]
    assert isinstance(excinfo.value.__cause__, MissingField)


@patch("airos.base._LOGGER")
@pytest.mark.asyncio
async def test_status_logs_redacted_data_on_invalid_value(
    mock_logger: MagicMock, airos8: AirOS8, device: FakeDevice
) -> None:
    """An invalid enum value is logged (redacted) via error()."""
    airos8.connected = True
    device.on(
        "GET",
        "/status.cgi",
        reply(payload=_fixture("userdata/mocked_invalid_wireless_mode.json")),
    )
    with pytest.raises(airos.exceptions.AirOSKeyDataMissingError) as excinfo:
        await airos8.status()

    assert isinstance(excinfo.value.__cause__, InvalidFieldValue)
    assert mock_logger.error.call_count == 1
    assert not mock_logger.exception.called

    logged = mock_logger.error.call_args[0][1]
    assert logged["wireless"]["essid"] == "REDACTED"
    assert logged["host"]["hostname"] == "REDACTED"
    assert logged["wireless"]["apmac"] == "00:11:22:33:89:AB"
    assert logged["interfaces"][2]["status"]["ipaddr"] == "127.0.0.3"


@patch("airos.base._LOGGER")
@pytest.mark.asyncio
async def test_status_logs_exception_on_missing_field(
    mock_logger: MagicMock, airos8: AirOS8, device: FakeDevice
) -> None:
    """A missing field is logged (redacted) via exception()."""
    airos8.connected = True
    status = _fixture("userdata/loco5ac_ap-ptp.json")
    del status["wireless"]
    device.on("GET", "/status.cgi", reply(payload=status))
    with pytest.raises(airos.exceptions.AirOSKeyDataMissingError) as excinfo:
        await airos8.status()

    assert isinstance(excinfo.value.__cause__, MissingField)
    assert mock_logger.exception.call_count == 1
    assert mock_logger.exception.call_args[0][1]["host"]["hostname"] == "REDACTED"


@pytest.mark.parametrize(
    ("handler", "expected"),
    [
        (reply(500), airos.exceptions.AirOSConnectionSetupError),
        (reply(403), airos.exceptions.AirOSConnectionAuthenticationError),
        (reply(body="<html>"), airos.exceptions.AirOSDataMissingError),
        (disconnect, airos.exceptions.AirOSDeviceConnectionError),
    ],
)
@pytest.mark.asyncio
async def test_status_errors(
    airos8: AirOS8,
    device: FakeDevice,
    handler: Handler,
    expected: type[Exception],
) -> None:
    """HTTP and transport failures map to library exceptions."""
    airos8.connected = True
    device.on("GET", "/status.cgi", handler)
    with pytest.raises(expected):
        await airos8.status()


# --- stakick() / provmode() / reboot() ---
@pytest.mark.asyncio
async def test_reconnect(airos8: AirOS8, device: FakeDevice) -> None:
    """stakick() posts the upper-cased MAC as a form.

    Response recorded from a NanoStation 5AC loco (v8.7.25).
    """
    airos8.connected = True
    device.on("POST", "/stakick.cgi", reply(payload=_fixture("stakick_ok.json")))
    assert await airos8.stakick("01:23:45:67:89:aB")

    sent = device.last("POST", "/stakick.cgi")
    assert sent.form == {"staif": "ath0", "staid": "01:23:45:67:89:AB"}
    assert sent.headers["Content-Type"] == "application/x-www-form-urlencoded"


@pytest.mark.parametrize(
    "payload",
    [{"status": 1, "message": "Failed"}, {}, []],
)
@pytest.mark.asyncio
async def test_stakick_not_fulfilled(
    airos8: AirOS8, device: FakeDevice, payload: Any
) -> None:
    """stakick() returns False unless the device reports status 0."""
    airos8.connected = True
    device.on("POST", "/stakick.cgi", reply(payload=payload))
    assert await airos8.stakick("01:23:45:67:89:aB") is False


@pytest.mark.asyncio
async def test_stakick_non_200_response(airos8: AirOS8, device: FakeDevice) -> None:
    """stakick() raises on a server error."""
    airos8.connected = True
    device.on("POST", "/stakick.cgi", reply(500))
    with pytest.raises(airos.exceptions.AirOSConnectionSetupError):
        await airos8.stakick("01:23:45:67:89:aB")


@pytest.mark.parametrize(("active", "action"), [(True, "start"), (False, "stop")])
@pytest.mark.asyncio
async def test_provmode(
    airos8: AirOS8, device: FakeDevice, active: bool, action: str
) -> None:
    """provmode() posts the right action.

    Response recorded from a NanoStation 5AC loco (v8.7.25).
    """
    airos8.connected = True
    device.on("POST", "/api/provmode", reply(payload=_fixture("provmode_ok.json")))
    assert await airos8.provmode(active=active)
    assert device.last("POST", "/api/provmode").form == {"action": action}


@pytest.mark.parametrize("payload", [{"ok": False}, {}, []])
@pytest.mark.asyncio
async def test_provmode_not_ok(
    airos8: AirOS8, device: FakeDevice, payload: Any
) -> None:
    """provmode() returns False unless the device reports ok."""
    airos8.connected = True
    device.on("POST", "/api/provmode", reply(payload=payload))
    assert await airos8.provmode(active=True) is False


@pytest.mark.parametrize(
    ("provmode", "expected"),
    [
        ({}, (False, None, None)),
        ({"status": 0, "timeout": 15}, (True, 0, 15)),
        ({"status": 2, "timeout": 899}, (True, 2, 899)),
    ],
)
@pytest.mark.asyncio
async def test_status_provmode(
    airos8: AirOS8,
    device: FakeDevice,
    provmode: dict[str, int],
    expected: tuple[bool, int | None, int | None],
) -> None:
    """status() exposes the provisioning mode state (values from a real device)."""
    airos8.connected = True
    data = _fixture("userdata/loco5ac_ap-ptp.json")
    data["provmode"] = provmode
    device.on("GET", "/status.cgi", reply(payload=data))
    result = (await airos8.status()).provmode
    assert (result.active, result.status, result.timeout) == expected


@pytest.mark.asyncio
async def test_provmode_non_200_response(airos8: AirOS8, device: FakeDevice) -> None:
    """provmode() raises on a server error."""
    airos8.connected = True
    device.on("POST", "/api/provmode", reply(500))
    with pytest.raises(airos.exceptions.AirOSConnectionSetupError):
        await airos8.provmode(active=True)


@pytest.mark.parametrize(
    ("payload", "expected"),
    [({"ok": True}, True), ({"ok": "true"}, True), ({"ok": False}, False)],
)
@pytest.mark.asyncio
async def test_reboot(
    airos8: AirOS8, device: FakeDevice, payload: dict[str, Any], expected: bool
) -> None:
    """reboot() posts the form and interprets the ok flag."""
    airos8.connected = True
    device.on("POST", "/reboot.cgi", reply(payload=payload))
    assert await airos8.reboot() is expected
    assert device.last("POST", "/reboot.cgi").form == {"reboot": "yes"}


# --- Host handling ---
@pytest.mark.parametrize(
    ("host", "use_ssl", "expected"),
    [
        ("192.168.1.20", True, "https://192.168.1.20"),
        ("192.168.1.20", False, "http://192.168.1.20"),
        ("http://device.local", True, "http://device.local"),
        ("https://10.0.0.1:8443/", False, "https://10.0.0.1:8443"),
        ("device.local:8080", True, "https://device.local:8080"),
        ("fe80::1", True, "https://[fe80::1]"),
        ("[fe80::1]:8443", False, "http://[fe80::1]:8443"),
        ("http://[2001:db8::1]:8080", True, "http://[2001:db8::1]:8080"),
    ],
)
def test_base_url(
    session: aiohttp.ClientSession, host: str, use_ssl: bool, expected: str
) -> None:
    """Ports and IPv6 literals are preserved in the base URL."""
    assert AirOS8(host, "u", "p", session, use_ssl=use_ssl).base_url == expected


# --- helpers.async_get_firmware_data() ---
@pytest.mark.asyncio
async def test_get_firmware_data_v8(
    device: FakeDevice, session: aiohttp.ClientSession
) -> None:
    """Firmware detection returns major version, hostname and MAC."""
    status = _fixture("userdata/loco5ac_ap-ptp.json")
    device.on("POST", "/api/auth", reply(payload={}))
    device.on("GET", "/status.cgi", reply(payload=status))
    result = await async_get_firmware_data(
        device.url, "user", "pass", session, use_ssl=False
    )

    assert result["fw_major"] == 8
    assert result["hostname"] == status["host"]["hostname"]
    assert result["mac"] == AirOS8.get_mac(status["interfaces"])["mac"]


@pytest.mark.asyncio
async def test_get_firmware_data_v6(
    device: FakeDevice, session: aiohttp.ClientSession
) -> None:
    """Firmware detection works for v6 devices via the login fallback."""
    _mock_v6_login(device)
    device.on(
        "GET",
        "/status.cgi",
        reply(payload=_fixture("userdata/NanoStation_loco_M5_v6.3.16_XM_ap.json")),
    )
    result = await async_get_firmware_data(
        device.url, "user", "pass", session, use_ssl=False
    )
    assert result["fw_major"] == 6


@pytest.mark.parametrize(
    ("handler", "expected"),
    [
        (reply(401), airos.exceptions.AirOSConnectionAuthenticationError),
        (reply(500), airos.exceptions.AirOSConnectionSetupError),
        (disconnect, airos.exceptions.AirOSDeviceConnectionError),
        (reply(body="not json"), airos.exceptions.AirOSDataMissingError),
    ],
)
@pytest.mark.asyncio
async def test_get_firmware_data_errors(
    device: FakeDevice,
    session: aiohttp.ClientSession,
    handler: Handler,
    expected: type[Exception],
) -> None:
    """Firmware detection re-raises library exceptions."""
    device.on("POST", "/api/auth", handler)
    with pytest.raises(expected):
        await async_get_firmware_data(
            device.url, "user", "pass", session, use_ssl=False
        )


@pytest.mark.asyncio
async def test_get_firmware_data_invalid_fwversion(
    device: FakeDevice, session: aiohttp.ClientSession
) -> None:
    """A status without a usable fwversion raises AirOSKeyDataMissingError."""
    status = _fixture("userdata/loco5ac_ap-ptp.json")
    status["host"].pop("fwversion")
    device.on("POST", "/api/auth", reply(payload={}))
    device.on("GET", "/status.cgi", reply(payload=status))
    with pytest.raises(airos.exceptions.AirOSKeyDataMissingError):
        await async_get_firmware_data(
            device.url, "user", "pass", session, use_ssl=False
        )
