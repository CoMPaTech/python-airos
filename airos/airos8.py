"""Ubiquiti AirOS 8."""

from __future__ import annotations

import asyncio
from http.cookies import SimpleCookie
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

        self._auth_cookie: str | None = None
        self._csrf_id: str | None = None
        self.connected: bool = False

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
        self,
        ct_json: bool = False,
        ct_form: bool = False,
    ) -> dict[str, str]:
        """Construct headers for an authenticated request."""
        headers = {}
        if ct_json:
            headers["Content-Type"] = "application/json"
        elif ct_form:
            headers["Content-Type"] = "application/x-www-form-urlencoded"

        if self._csrf_id:
            headers["X-CSRF-ID"] = self._csrf_id

        if self._auth_cookie:
            headers["Cookie"] = f"AIROS_{self._auth_cookie}"

        return headers

    def _store_auth_data(self, response: aiohttp.ClientResponse) -> None:
        """Parse the response from a successful login and store auth data."""
        self._csrf_id = response.headers.get("X-CSRF-ID")

        # Parse all Set-Cookie headers to ensure we don't miss AIROS_* cookie
        cookie = SimpleCookie()
        for set_cookie in response.headers.getall("Set-Cookie", []):
            cookie.load(set_cookie)
        for key, morsel in cookie.items():
            if key.startswith("AIROS_"):
                self._auth_cookie = morsel.key[6:] + "=" + morsel.value
                break

    async def _request_json(
        self,
        method: str,
        url: str,
        headers: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
        form_data: dict[str, Any] | None = None,
        authenticated: bool = False,
        ct_json: bool = False,
        ct_form: bool = False,
    ) -> dict[str, Any] | Any:
        """Make an authenticated API request and return JSON response."""
        # Pass the content type flags to the header builder
        request_headers = (
            self._get_authenticated_headers(ct_json=ct_json, ct_form=ct_form)
            if authenticated
            else {}
        )
        if headers:
            request_headers.update(headers)

        try:
            if url != self._login_url and not self.connected:
                _LOGGER.error("Not connected, login first")
                raise AirOSDeviceConnectionError from None

            async with self.session.request(
                method,
                url,
                json=json_data,
                data=form_data,
                headers=request_headers,  # Pass the constructed headers
            ) as response:
                response.raise_for_status()
                response_text = await response.text()
                _LOGGER.debug("Successfully fetched JSON from %s", url)

                # If this is the login request, we need to store the new auth data
                if url == self._login_url:
                    self._store_auth_data(response)
                    self.connected = True

                return json.loads(response_text)
        except aiohttp.ClientResponseError as err:
            _LOGGER.error(
                "Request to %s failed with status %s: %s", url, err.status, err.message
            )
            if err.status == 401:
                raise AirOSConnectionAuthenticationError from err
            raise AirOSConnectionSetupError from err
        except (TimeoutError, aiohttp.ClientError) as err:
            _LOGGER.exception("Error during API call to %s", url)
            raise AirOSDeviceConnectionError from err
        except json.JSONDecodeError as err:
            _LOGGER.error("Failed to decode JSON from %s", url)
            raise AirOSDataMissingError from err
        except asyncio.CancelledError:
            _LOGGER.warning("Request to %s was cancelled", url)
            raise

    async def login(self) -> None:
        """Login to AirOS device."""
        payload = {"username": self.username, "password": self.password}
        try:
            await self._request_json("POST", self._login_url, json_data=payload)
        except (AirOSConnectionAuthenticationError, AirOSConnectionSetupError) as err:
            raise AirOSConnectionSetupError("Failed to login to AirOS device") from err

    async def status(self) -> AirOSData:
        """Retrieve status from the device."""
        response = await self._request_json(
            "GET", self._status_cgi_url, authenticated=True
        )

        try:
            adjusted_json = self.derived_data(response)
            return AirOSData.from_dict(adjusted_json)
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

    async def update_check(self, force: bool = False) -> dict[str, Any]:
        """Check for firmware updates."""
        if force:
            return await self._request_json(
                "POST",
                self._update_check_url,
                json_data={"force": True},
                authenticated=True,
                ct_form=True,
            )
        return await self._request_json(
            "POST",
            self._update_check_url,
            json_data={},
            authenticated=True,
            ct_json=True,
        )

    async def stakick(self, mac_address: str | None = None) -> bool:
        """Reconnect client station."""
        if not mac_address:
            _LOGGER.error("Device mac-address missing")
            raise AirOSDataMissingError from None

        payload = {"staif": "ath0", "staid": mac_address.upper()}

        await self._request_json(
            "POST",
            self._stakick_cgi_url,
            form_data=payload,
            ct_form=True,
            authenticated=True,
        )
        return True

    async def provmode(self, active: bool = False) -> bool:
        """Set provisioning mode."""
        action = "stop"
        if active:
            action = "start"

        payload = {"action": action}
        await self._request_json(
            "POST",
            self._provmode_url,
            form_data=payload,
            ct_form=True,
            authenticated=True,
        )
        return True

    async def warnings(self) -> dict[str, Any]:
        """Get warnings."""
        return await self._request_json("GET", self._warnings_url, authenticated=True)

    async def progress(self) -> dict[str, Any]:
        """Get download progress for updates."""
        payload: dict[str, Any] = {}
        return await self._request_json(
            "POST",
            self._download_progress_url,
            json_data=payload,
            ct_json=True,
            authenticated=True,
        )

    async def download(self) -> dict[str, Any]:
        """Download new firmware."""
        payload: dict[str, Any] = {}
        return await self._request_json(
            "POST",
            self._download_url,
            json_data=payload,
            ct_json=True,
            authenticated=True,
        )

    async def install(self) -> dict[str, Any]:
        """Install new firmware."""
        payload: dict[str, Any] = {"do_update": 1}
        return await self._request_json(
            "POST",
            self._install_url,
            json_data=payload,
            ct_json=True,
            authenticated=True,
        )
