"""Ubiquiti AirOS 8."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any
from urllib.parse import urlparse

import aiohttp
from mashumaro.exceptions import InvalidFieldValue, MissingField

from .data import (
    AirOS8Data as AirOSData,
    DerivedWirelessMode,
    DerivedWirelessRole,
    redact_data_smart,
)
from .exceptions import (
    AirOSConnectionAuthenticationError,
    AirOSConnectionSetupError,
    AirOSDataMissingError,
    AirOSDeviceConnectionError,
    AirOSKeyDataMissingError,
)

_LOGGER = logging.getLogger(__name__)


class AirOS:
    """AirOS 8 connection class."""

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        session: aiohttp.ClientSession,
        use_ssl: bool = True,
    ):
        """Initialize AirOS8 class."""
        self.username = username
        self.password = password

        parsed_host = urlparse(host)
        scheme = (
            parsed_host.scheme
            if parsed_host.scheme
            else ("https" if use_ssl else "http")
        )
        hostname = parsed_host.hostname if parsed_host.hostname else host

        self.base_url = f"{scheme}://{hostname}"

        self.session = session

        self._login_url = f"{self.base_url}/api/auth"
        self._status_cgi_url = f"{self.base_url}/status.cgi"
        self._stakick_cgi_url = f"{self.base_url}/stakick.cgi"
        self._provmode_url = f"{self.base_url}/api/provmode"
        self._warnings_url = f"{self.base_url}/api/warnings"
        self._update_check_url = f"{self.base_url}/api/fw/update-check"
        self._download_url = f"{self.base_url}/api/fw/download"
        self._download_progress_url = f"{self.base_url}/api/fw/download-progress"
        self._install_url = f"{self.base_url}/fwflash.cgi"
        self.current_csrf_token: str | None = None

        self._use_json_for_login_post = False

        self._common_headers = {
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Sec-Fetch-Site": "same-origin",
            "Accept-Language": "en-US,nl;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Sec-Fetch-Mode": "cors",
            "Origin": self.base_url,
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Safari/605.1.15",
            "Referer": self.base_url + "/",
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "empty",
            "X-Requested-With": "XMLHttpRequest",
        }

        self.connected = False

    @staticmethod
    def derived_data(response: dict[str, Any]) -> dict[str, Any]:
        """Add derived data to the device response."""
        derived: dict[str, Any] = {
            "station": False,
            "access_point": False,
            "ptp": False,
            "ptmp": False,
            "role": DerivedWirelessRole.STATION,
            "mode": DerivedWirelessMode.PTP,
        }

        # Access Point / Station vs PTP/PtMP
        wireless_mode = response.get("wireless", {}).get("mode", "")
        match wireless_mode:
            case "ap-ptmp":
                derived["access_point"] = True
                derived["ptmp"] = True
                derived["role"] = DerivedWirelessRole.ACCESS_POINT
                derived["mode"] = DerivedWirelessMode.PTMP
            case "sta-ptmp":
                derived["station"] = True
                derived["ptmp"] = True
                derived["mode"] = DerivedWirelessMode.PTMP
            case "ap-ptp":
                derived["access_point"] = True
                derived["ptp"] = True
                derived["role"] = DerivedWirelessRole.ACCESS_POINT
            case "sta-ptp":
                derived["station"] = True
                derived["ptp"] = True

        # INTERFACES
        addresses = {}
        interface_order = ["br0", "eth0", "ath0"]

        interfaces = response.get("interfaces", [])

        # No interfaces, no mac, no usability
        if not interfaces:
            raise AirOSKeyDataMissingError from None

        for interface in interfaces:
            if interface["enabled"]:  # Only consider if enabled
                addresses[interface["ifname"]] = interface["hwaddr"]

        # Fallback take fist alternate interface found
        derived["mac"] = interfaces[0]["hwaddr"]
        derived["mac_interface"] = interfaces[0]["ifname"]

        for interface in interface_order:
            if interface in addresses:
                derived["mac"] = addresses[interface]
                derived["mac_interface"] = interface
                break

        response["derived"] = derived

        return response

    def _get_authenticated_headers(
        self, ct_json: bool = False, ct_form: bool = False
    ) -> dict[str, Any]:
        """Return common headers with CSRF token and optional Content-Type."""
        headers = {**self._common_headers}
        if self.current_csrf_token:
            headers["X-CSRF-ID"] = self.current_csrf_token
        if ct_json:
            headers["Content-Type"] = "application/json"
        if ct_form:
            headers["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8"
        return headers

    async def _api_call(
        self, method: str, url: str, headers: dict[str, Any], **kwargs: Any
    ) -> dict[str, Any]:
        """Make API call."""
        if url != self._login_url and not self.connected:
            _LOGGER.error("Not connected, login first")
            raise AirOSDeviceConnectionError from None

        try:
            async with self.session.request(
                method, url, headers=headers, **kwargs
            ) as response:
                response_text = await response.text()
                result = {"response": response, "response_text": response_text}
                return result
        except (TimeoutError, aiohttp.ClientError) as err:
            _LOGGER.exception("Error during API call to %s: %s", url, err)
            raise AirOSDeviceConnectionError from err
        except asyncio.CancelledError:
            _LOGGER.info("API task to %s was cancelled", url)
            raise

    async def _request_json(
        self, method: str, url: str, headers: dict[str, Any], **kwargs: Any
    ) -> dict[str, Any] | Any:
        """Return JSON from API call."""
        result = await self._api_call(method, url, headers=headers, **kwargs)
        response = result.get("response", {})
        response_text = result.get("response_text", "")

        match response.status:
            case 200:
                pass
            case 403:
                _LOGGER.error("Authentication denied.")
                raise AirOSConnectionAuthenticationError from None
            case _:
                _LOGGER.error(
                    "API call to %s failed with status %d: %s",
                    url,
                    response.status,
                    response_text,
                )
                raise AirOSDeviceConnectionError from None

        try:
            return json.loads(await response.text())
        except json.JSONDecodeError as err:
            _LOGGER.exception("JSON Decode Error in API response from %s", url)
            raise AirOSDataMissingError from err

    async def login(self) -> bool:
        """Log in to the device assuring cookies and tokens set correctly."""
        # --- Step 0: Pre-inject the 'ok=1' cookie before login POST (mimics curl) ---
        self.session.cookie_jar.update_cookies({"ok": "1"})

        # --- Step 1: Attempt Login to /api/auth (This now sets all session cookies and the CSRF token) ---
        payload = {
            "username": self.username,
            "password": self.password,
        }

        request_headers = self._get_authenticated_headers(ct_form=True)
        if self._use_json_for_login_post:
            request_headers = self._get_authenticated_headers(ct_json=True)
            result = await self._api_call(
                "POST", self._login_url, headers=request_headers, json=payload
            )
        else:
            result = await self._api_call(
                "POST", self._login_url, headers=request_headers, data=payload
            )
        response = result.get("response", {})
        response_text = result.get("response_text", "")

        if response.status == 403:
            _LOGGER.error("Authentication denied.")
            raise AirOSConnectionAuthenticationError from None

        for _, morsel in response.cookies.items():
            # If the AIROS_ cookie was parsed but isn't automatically added to the jar, add it manually
            if (
                morsel.key.startswith("AIROS_")
                and morsel.key not in self.session.cookie_jar
            ):
                # `SimpleCookie`'s Morsel objects are designed to be compatible with cookie jars.
                # We need to set the domain if it's missing, otherwise the cookie might not be sent.
                # For IP addresses, the domain is typically blank.
                # aiohttp's jar should handle it, but for explicit control:
                if not morsel.get("domain"):
                    morsel["domain"] = (
                        response.url.host
                    )  # Set to the host that issued it
                self.session.cookie_jar.update_cookies(
                    {
                        morsel.key: morsel.output(header="")[len(morsel.key) + 1 :]
                        .split(";")[0]
                        .strip()
                    },
                    response.url,
                )
                # The update_cookies method can take a SimpleCookie morsel directly or a dict.
                # The morsel.output method gives 'NAME=VALUE; Path=...; HttpOnly'
                # We just need 'NAME=VALUE' or the morsel object itself.
                # Let's use the morsel directly which is more robust.
                # Alternatively: self.session.cookie_jar.update_cookies({morsel.key: morsel.value}) might work if it's simpler.
                # Aiohttp's update_cookies takes a dict mapping name to value.
                # To pass the full morsel with its attributes, we need to add it to the jar's internal structure.
                # Simpler: just ensure the key-value pair is there for simple jar.

                # Let's try the direct update of the key-value
                self.session.cookie_jar.update_cookies({morsel.key: morsel.value})

        new_csrf_token = response.headers.get("X-CSRF-ID")
        if new_csrf_token:
            self.current_csrf_token = new_csrf_token
        else:
            return False

        # Re-check cookies in self.session.cookie_jar AFTER potential manual injection
        airos_cookie_found = False
        ok_cookie_found = False
        if not self.session.cookie_jar:  # pragma: no cover
            _LOGGER.exception(
                "COOKIE JAR IS EMPTY after login POST. This is a major issue."
            )
            raise AirOSConnectionSetupError from None
        for cookie in self.session.cookie_jar:  # pragma: no cover
            if cookie.key.startswith("AIROS_"):
                airos_cookie_found = True
            if cookie.key == "ok":
                ok_cookie_found = True

        if not airos_cookie_found and not ok_cookie_found:
            raise AirOSConnectionSetupError from None  # pragma: no cover

        if response.status != 200:
            log = f"Login failed with status {response.status}."
            _LOGGER.error(log)
            raise AirOSConnectionAuthenticationError from None

        try:
            json.loads(response_text)
            self.connected = True
            return True
        except json.JSONDecodeError as err:
            _LOGGER.exception("JSON Decode Error")
            raise AirOSDataMissingError from err

    async def status(self) -> AirOSData:
        """Retrieve status from the device."""
        # --- Step 2: Verify authenticated access by fetching status.cgi ---
        request_headers = self._get_authenticated_headers()
        response = await self._request_json(
            "GET", self._status_cgi_url, headers=request_headers
        )

        try:
            adjusted_json = self.derived_data(response)
            airos_data = AirOSData.from_dict(adjusted_json)
            return airos_data
        except InvalidFieldValue as err:
            # Log with .error() as this is a specific, known type of issue
            redacted_data = redact_data_smart(response)
            _LOGGER.error(
                "Failed to deserialize AirOS data due to an invalid field value: %s",
                redacted_data,
            )
            raise AirOSKeyDataMissingError from err
        except MissingField as err:
            # Log with .exception() for a full stack trace
            redacted_data = redact_data_smart(response)
            _LOGGER.exception(
                "Failed to deserialize AirOS data due to a missing field: %s",
                redacted_data,
            )
            raise AirOSKeyDataMissingError from err

    async def stakick(self, mac_address: str | None = None) -> bool:
        """Reconnect client station."""
        if not mac_address:
            _LOGGER.error("Device mac-address missing")
            raise AirOSDataMissingError from None

        request_headers = self._get_authenticated_headers(ct_form=True)
        payload = {"staif": "ath0", "staid": mac_address.upper()}

        result = await self._api_call(
            "POST", self._stakick_cgi_url, headers=request_headers, data=payload
        )
        response = result.get("response", {})
        if response.status == 200:
            return True

        response_text = result.get("response_text", "")
        log = f"Unable to restart connection response status {response.status} with {response_text}"
        _LOGGER.error(log)
        return False

    async def provmode(self, active: bool = False) -> bool:
        """Set provisioning mode."""
        request_headers = self._get_authenticated_headers(ct_form=True)

        action = "stop"
        if active:
            action = "start"

        payload = {"action": action}
        result = await self._api_call(
            "POST", self._provmode_url, headers=request_headers, data=payload
        )
        response = result.get("response", {})
        if response.status == 200:
            return True

        response_text = result.get("response_text", "")
        log = f"Unable to change provisioning mode response status {response.status} with {response_text}"
        _LOGGER.error(log)
        return False

    async def warnings(self) -> dict[str, Any]:
        """Get warnings."""
        request_headers = self._get_authenticated_headers()
        return await self._request_json(
            "GET", self._warnings_url, headers=request_headers
        )

    async def update_check(self, force: bool = False) -> dict[str, Any]:
        """Check firmware update available."""
        request_headers = self._get_authenticated_headers(ct_json=True)

        payload: dict[str, Any] = {}
        if force:
            payload = {"force": "yes"}
            request_headers = self._get_authenticated_headers(ct_form=True)
        return await self._request_json(
            "POST", self._update_check_url, headers=request_headers, json=payload
        )

    async def progress(self) -> dict[str, Any]:
        """Get download progress for updates."""
        request_headers = self._get_authenticated_headers(ct_json=True)
        payload: dict[str, Any] = {}

        return await self._request_json(
            "POST", self._download_progress_url, headers=request_headers, json=payload
        )

    async def download(self) -> dict[str, Any]:
        """Download new firmware."""
        request_headers = self._get_authenticated_headers(ct_json=True)
        payload: dict[str, Any] = {}
        return await self._request_json(
            "POST", self._download_url, headers=request_headers, json=payload
        )

    async def install(self) -> dict[str, Any]:
        """Install new firmware."""
        request_headers = self._get_authenticated_headers(ct_form=True)
        payload: dict[str, Any] = {"do_update": 1}
        return await self._request_json(
            "POST", self._install_url, headers=request_headers, json=payload
        )
