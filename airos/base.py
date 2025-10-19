"""Ubiquiti AirOS base class."""

from __future__ import annotations

from abc import ABC
import asyncio
from collections.abc import Callable
import contextlib
from http.cookies import SimpleCookie
import json
import logging
import time
from typing import Any, Generic, TypeVar
from urllib.parse import urlparse

import aiohttp
from mashumaro.exceptions import InvalidFieldValue, MissingField
from yarl import URL

from .data import (
    AirOSDataBaseClass,
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
    AirOSMultipleMatchesFoundException,
    AirOSUrlNotFoundError,
)
from .model_map import UispAirOSProductMapper

_LOGGER = logging.getLogger(__name__)

AirOSDataModel = TypeVar("AirOSDataModel", bound=AirOSDataBaseClass)


class AirOS(ABC, Generic[AirOSDataModel]):
    """AirOS connection class."""

    data_model: type[AirOSDataModel]

    def __init__(
        self,
        data_model: type[AirOSDataModel],
        host: str,
        username: str,
        password: str,
        session: aiohttp.ClientSession,
        use_ssl: bool = True,
    ):
        """Initialize AirOS class."""
        self.data_model = data_model
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

        # self.session = session
        self.session = aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(verify_ssl=False, force_close=True),
            cookie_jar=aiohttp.CookieJar(),
        )

        self.api_version: int = 8

        self._use_json_for_login_post = False
        self._auth_cookie: str | None = None
        self._csrf_id: str | None = None
        self.connected: bool = False
        self.current_csrf_token: str | None = None

        # Mostly 8.x API endpoints, login/status are the same in 6.x
        self._login_urls = {
            "default": f"{self.base_url}/api/auth",
            "v6_login": f"{self.base_url}/login.cgi",
        }
        self._status_cgi_url = f"{self.base_url}/status.cgi"
        # Presumed 8.x only endpoints
        self._stakick_cgi_url = f"{self.base_url}/stakick.cgi"
        self._provmode_url = f"{self.base_url}/api/provmode"
        self._warnings_url = f"{self.base_url}/api/warnings"
        self._update_check_url = f"{self.base_url}/api/fw/update-check"
        self._download_url = f"{self.base_url}/api/fw/download"
        self._download_progress_url = f"{self.base_url}/api/fw/download-progress"
        self._install_url = f"{self.base_url}/fwflash.cgi"

    @staticmethod
    def derived_wireless_data(
        derived: dict[str, Any], response: dict[str, Any]
    ) -> dict[str, Any]:
        """Add derived wireless data to the device response."""
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
        return derived

    @staticmethod
    def _derived_data_helper(
        response: dict[str, Any],
        derived_wireless_data_func: Callable[
            [dict[str, Any], dict[str, Any]], dict[str, Any]
        ],
    ) -> dict[str, Any]:
        """Add derived data to the device response."""
        sku: str = "UNKNOWN"

        devmodel = (response.get("host") or {}).get("devmodel", "UNKNOWN")
        try:
            sku = UispAirOSProductMapper().get_sku_by_devmodel(devmodel)
        except KeyError:
            _LOGGER.warning(
                "Unknown SKU/Model ID for %s. Please report at "
                "https://github.com/CoMPaTech/python-airos/issues so we can add support.",
                devmodel,
            )
            sku = "UNKNOWN"
        except AirOSMultipleMatchesFoundException as err:  # pragma: no cover
            _LOGGER.warning(
                "Multiple SKU/Model ID matches found for model '%s': %s. Please report at "
                "https://github.com/CoMPaTech/python-airos/issues so we can add support.",
                devmodel,
                err,
            )
            sku = "AMBIGUOUS"

        derived: dict[str, Any] = {
            "station": False,
            "access_point": False,
            "ptp": False,
            "ptmp": False,
            "role": DerivedWirelessRole.STATION,
            "mode": DerivedWirelessMode.PTP,
            "sku": sku,
        }
        # WIRELESS
        derived = derived_wireless_data_func(derived, response)

        # INTERFACES
        addresses = {}
        interface_order = ["br0", "eth0", "ath0"]

        interfaces = response.get("interfaces", [])

        # No interfaces, no mac, no usability
        if not interfaces:
            _LOGGER.error("Failed to determine interfaces from AirOS data")
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

    def derived_data(self, response: dict[str, Any]) -> dict[str, Any]:
        """Add derived data to the device response (instance method for polymorphism)."""
        return self._derived_data_helper(response, self.derived_wireless_data)

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

        if self._csrf_id:  # pragma: no cover
            _LOGGER.error("TESTv%s - CSRF ID found %s", self.api_version, self._csrf_id)
            headers["X-CSRF-ID"] = self._csrf_id

        """
        if self._auth_cookie:  # pragma: no cover
            _LOGGER.error(
                "TESTv%s - auth_cookie found: AIROS_%s",
                self.api_version,
                self._auth_cookie,
            )
            # headers["Cookie"] = f"AIROS_{self._auth_cookie}"
            headers["Cookie"] = self._auth_cookie
        """

        return headers

    def _store_auth_data(self, response: aiohttp.ClientResponse) -> None:
        """Parse the response from a successful login and store auth data."""
        self._csrf_id = response.headers.get("X-CSRF-ID")

        # Parse all Set-Cookie headers to ensure we don't miss AIROS_* cookie
        cookie = SimpleCookie()
        for set_cookie in response.headers.getall("Set-Cookie", []):
            _LOGGER.error(
                "TESTv%s - regular cookie handling: %s", self.api_version, set_cookie
            )
            cookie.load(set_cookie)
        for key, morsel in cookie.items():
            _LOGGER.error(
                "TESTv%s - AIROS_cookie handling: %s with %s",
                self.api_version,
                key,
                morsel.value,
            )
            if key.startswith("AIROS_"):
                self._auth_cookie = morsel.key[6:] + "=" + morsel.value
                break

    async def _request_json(
        self,
        method: str,
        url: str,
        headers: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
        form_data: dict[str, Any] | aiohttp.FormData | None = None,
        authenticated: bool = False,
        ct_json: bool = False,
        ct_form: bool = False,
        allow_redirects: bool = True,
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

        # Potential XM fix - not sure, might have been login issue
        if self.api_version == 6 and url.startswith(self._status_cgi_url):
            # Ensure all HAR-matching headers are present
            request_headers["Accept"] = "application/json, text/javascript, */*; q=0.01"
            request_headers["Accept-Encoding"] = "gzip, deflate, br, zstd"
            request_headers["Accept-Language"] = "pl"
            request_headers["Cache-Control"] = "no-cache"
            request_headers["Connection"] = "keep-alive"
            request_headers["Host"] = (
                urlparse(self.base_url).hostname or "192.168.1.142"
            )
            request_headers["Pragma"] = "no-cache"
            request_headers["Referer"] = f"{self.base_url}/index.cgi"
            request_headers["Sec-Fetch-Dest"] = "empty"
            request_headers["Sec-Fetch-Mode"] = "cors"
            request_headers["Sec-Fetch-Site"] = "same-origin"
            request_headers["User-Agent"] = (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"
            )
            request_headers["X-Requested-With"] = "XMLHttpRequest"
            request_headers["sec-ch-ua"] = (
                '"Google Chrome";v="141", "Not?A_Brand";v="8", "Chromium";v="141"'
            )
            request_headers["sec-ch-ua-mobile"] = "?0"
            request_headers["sec-ch-ua-platform"] = '"Windows"'
        if url.startswith(self._login_urls["v6_login"]):
            request_headers["Referrer"] = f"{self.base_url}/login.cgi"
            request_headers["Origin"] = self.base_url
            request_headers["Accept"] = (
                "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7"
            )
            request_headers["User-Agent"] = (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"
            )
            request_headers["Sec-Fetch-Dest"] = "document"
            request_headers["Sec-Fetch-Mode"] = "navigate"
            request_headers["Sec-Fetch-Site"] = "same-origin"
            request_headers["Sec-Fetch-User"] = "?1"
            request_headers["Cache-Control"] = "no-cache"
            request_headers["Pragma"] = "no-cache"

        try:
            if (
                url not in self._login_urls.values()
                and url != f"{self.base_url}/"
                and not self.connected
            ):
                _LOGGER.error("Not connected, login first")
                raise AirOSDeviceConnectionError from None

            if self.api_version == 6 and url.startswith(self._status_cgi_url):
                _LOGGER.error(
                    "TESTv%s - adding timestamp to status url!", self.api_version
                )
                timestamp = int(time.time() * 1000)
                url = f"{self._status_cgi_url}?_={timestamp}"

            _LOGGER.error("TESTv%s - Trying with URL: %s", self.api_version, url)
            async with self.session.request(
                method,
                url,
                json=json_data,
                data=form_data,
                headers=request_headers,  # Pass the constructed headers
                allow_redirects=allow_redirects,
            ) as response:
                _LOGGER.error(
                    "TESTv%s - Response code: %s", self.api_version, response.status
                )
                _LOGGER.error(
                    "TESTv%s - Response headers: %s",
                    self.api_version,
                    dict(response.headers),
                )
                _LOGGER.error(
                    "TESTv%s - Response history: %s", self.api_version, response.history
                )
                _LOGGER.error(
                    "TESTv%s - Session cookies: %s",
                    self.api_version,
                    self.session.cookie_jar.filter_cookies(URL(url)),
                )

                # v6 responds with a 302 redirect and empty body
                if not url.startswith(self._login_urls["v6_login"]):
                    self.api_version = 6
                    response.raise_for_status()

                response_text = await response.text()
                _LOGGER.error("Successfully fetched %s from %s", response_text, url)
                if not response_text.strip():
                    _LOGGER.error(
                        "TESTv%s - Empty response from %s despite %s",
                        self.api_version,
                        url,
                        response.status,
                    )

                # If this is the login request, we need to store the new auth data
                if url in self._login_urls.values():
                    self._store_auth_data(response)
                    self.connected = True

                _LOGGER.error("TESTv%s - response: %s", self.api_version, response_text)

                location = response.headers.get("Location")
                if location and isinstance(location, str) and location.startswith("/"):
                    _LOGGER.error(
                        "TESTv%s - Following redirect to: %s",
                        self.api_version,
                        location,
                    )
                    await self._request_json(
                        "GET",
                        f"{self.base_url}{location}",
                        headers={
                            "Referer": self._login_urls["v6_login"],
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
                        },
                        authenticated=True,
                        allow_redirects=False,
                    )
                else:
                    _LOGGER.error(
                        "TESTv%s - no location header found to follow in response to %s",
                        self.api_version,
                        url,
                    )
                # V6 responds with empty body on login, not JSON
                if url.startswith(self._login_urls["v6_login"]):
                    return {}

                return json.loads(response_text)
        except aiohttp.ClientResponseError as err:
            _LOGGER.error(
                "Request to %s failed with status %s: %s", url, err.status, err.message
            )
            if err.status in [401, 403]:
                raise AirOSConnectionAuthenticationError from err
            if err.status in [404]:
                raise AirOSUrlNotFoundError from err
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
            _LOGGER.error("TESTv%s - Trying default v8 login URL", self.api_version)
            await self._request_json(
                "POST", self._login_urls["default"], json_data=payload
            )
        except AirOSUrlNotFoundError:
            _LOGGER.error(
                "TESTv%s - gives URL not found, trying alternative v6 URL",
                self.api_version,
            )
            # Try next URL
        except AirOSConnectionSetupError as err:
            _LOGGER.error("TESTv%s - failed to login to v8 URL", self.api_version)
            raise AirOSConnectionSetupError("Failed to login to AirOS device") from err
        else:
            _LOGGER.error("TESTv%s - returning from v8 login", self.api_version)
            return

        # Start of v6, go for cookies
        _LOGGER.error(
            "TESTv%s - Trying to get /index.cgi first for cookies", self.api_version
        )
        with contextlib.suppress(Exception):
            cookieresponse = await self._request_json(
                "GET",
                f"{self.base_url}/index.cgi",
                authenticated=True,
                headers={
                    "Referer": f"{self.base_url}/login.cgi",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
                },
            )
            _LOGGER.error(
                "TESTv%s - Cookie response: %s", self.api_version, cookieresponse
            )
            if isinstance(cookieresponse, aiohttp.ClientResponse):
                _LOGGER.debug(
                    "TESTv%s - Finalization redirect chain: %s",
                    self.api_version,
                    cookieresponse.history,
                )
            else:
                _LOGGER.debug(
                    "TESTv%s - Finalization response is not a ClientResponse: %s",
                    self.api_version,
                    type(cookieresponse),
                )

        v6_simple_multipart_form_data = aiohttp.FormData()
        v6_simple_multipart_form_data.add_field("uri", "/index.cgi")
        v6_simple_multipart_form_data.add_field("username", self.username)
        v6_simple_multipart_form_data.add_field("password", self.password)

        _LOGGER.debug(
            "TESTv%s !!!REDACT THIS!!!! Form payload: %s",
            self.api_version,
            v6_simple_multipart_form_data(),
        )

        login_headers = {
            "Referer": self._login_urls["v6_login"],
        }

        _LOGGER.error("TESTv%s - start v6 attempts", self.api_version)
        # --- ATTEMPT B: Simple Payload (multipart/form-data) ---
        try:
            _LOGGER.error(
                "TESTv%s - Trying V6 POST to %s with SIMPLE multipart/form-data",
                self.api_version,
                self._login_urls["v6_login"],
            )
            await self._request_json(
                "POST",
                self._login_urls["v6_login"],
                headers=login_headers,
                form_data=v6_simple_multipart_form_data,
                ct_form=False,
                ct_json=False,
                authenticated=False,
                allow_redirects=False,
            )
        except (AirOSUrlNotFoundError, AirOSConnectionSetupError) as err:
            _LOGGER.error(
                "TESTv%s - V6 simple multipart failed (%s) on %s. Error: %s",
                self.api_version,
                type(err).__name__,
                self._login_urls["v6_login"],
                err,
            )
        except AirOSConnectionAuthenticationError:
            _LOGGER.error(
                "TESTv%s - autherror during extended multipart", self.api_version
            )
            raise
        else:
            _LOGGER.error("TESTv%s - returning from simple multipart", self.api_version)
            # Finalize session by visiting /index.cgi
            _LOGGER.error(
                "TESTv%s - Finalizing session with GET to /index.cgi", self.api_version
            )
            with contextlib.suppress(Exception):
                await self._request_json(
                    "GET",
                    f"{self.base_url}/index.cgi",
                    headers={
                        "Referer": f"{self.base_url}/login.cgi",
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
                    },
                    authenticated=True,
                    allow_redirects=True,
                )
            return  # Success

    async def status(self) -> AirOSDataModel:
        """Retrieve status from the device."""
        status_headers = {
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "X-Requested-With": "XMLHttpRequest",
        }
        response = await self._request_json(
            "GET", self._status_cgi_url, authenticated=True, headers=status_headers
        )

        try:
            adjusted_json = self.derived_data(response)
            return self.data_model.from_dict(adjusted_json)
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
