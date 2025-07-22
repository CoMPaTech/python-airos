"""Ubiquiti AirOS 8 module for Home Assistant Core."""

from __future__ import annotations

import json
import logging
from urllib.parse import urlparse

import aiohttp
from mashumaro.exceptions import InvalidFieldValue, MissingField

from .airos8data import AirOSData
from .exceptions import (
    ConnectionAuthenticationError,
    ConnectionSetupError,
    DataMissingError,
    DeviceConnectionError,
    KeyDataMissingError,
)

logger = logging.getLogger(__name__)


class AirOS:
    """Set up connection to AirOS."""

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

        self._login_url = f"{self.base_url}/api/auth"  # AirOS 8
        self._status_cgi_url = f"{self.base_url}/status.cgi"  # AirOS 8
        self._stakick_cgi_url = f"{self.base_url}/stakick.cgi"  # AirOS 8
        self.current_csrf_token = None
        self.warnings_cache = []

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

    async def login(self) -> bool:
        """Log in to the device assuring cookies and tokens set correctly."""
        # --- Step 0: Pre-inject the 'ok=1' cookie before login POST (mimics curl) ---
        self.session.cookie_jar.update_cookies({"ok": "1"})

        # --- Step 1: Attempt Login to /api/auth (This now sets all session cookies and the CSRF token) ---
        login_payload = {
            "username": self.username,
            "password": self.password,
        }

        login_request_headers = {**self._common_headers}

        post_data = None
        if self._use_json_for_login_post:
            login_request_headers["Content-Type"] = "application/json"
            post_data = json.dumps(login_payload)
        else:
            login_request_headers["Content-Type"] = (
                "application/x-www-form-urlencoded; charset=UTF-8"
            )
            post_data = login_payload

        try:
            async with self.session.post(
                self._login_url,
                data=post_data,
                headers=login_request_headers,
            ) as response:
                if not response.cookies:
                    logger.exception("Empty cookies after login, bailing out.")
                    raise ConnectionSetupError from None
                else:
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
                                    morsel.key: morsel.output(header="")[
                                        len(morsel.key) + 1 :
                                    ]
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
                            self.session.cookie_jar.update_cookies(
                                {morsel.key: morsel.value}
                            )

                new_csrf_token = response.headers.get("X-CSRF-ID")
                if new_csrf_token:
                    self.current_csrf_token = new_csrf_token
                else:
                    return

                # Re-check cookies in self.session.cookie_jar AFTER potential manual injection
                airos_cookie_found = False
                ok_cookie_found = False
                if not self.session.cookie_jar:  # pragma: no cover
                    logger.exception(
                        "COOKIE JAR IS EMPTY after login POST. This is a major issue."
                    )
                    raise ConnectionSetupError from None
                for cookie in self.session.cookie_jar:  # pragma: no cover
                    if cookie.key.startswith("AIROS_"):
                        airos_cookie_found = True
                    if cookie.key == "ok":
                        ok_cookie_found = True

                if not airos_cookie_found and not ok_cookie_found:
                    raise ConnectionSetupError from None  # pragma: no cover

                response_text = await response.text()

                if response.status == 200:
                    try:
                        json.loads(response_text)
                        self.connected = True
                        return True
                    except json.JSONDecodeError as err:
                        logger.exception("JSON Decode Error")
                        raise DataMissingError from err

                else:
                    log = f"Login failed with status {response.status}. Full Response: {response.text}"
                    logger.error(log)
                    raise ConnectionAuthenticationError from None
        except (
            aiohttp.ClientError,
            aiohttp.client_exceptions.ConnectionTimeoutError,
        ) as err:
            logger.exception("Error during login")
            raise DeviceConnectionError from err

    async def status(self) -> AirOSData:
        """Retrieve status from the device."""
        if not self.connected:
            logger.error("Not connected, login first")
            raise DeviceConnectionError from None

        # --- Step 2: Verify authenticated access by fetching status.cgi ---
        authenticated_get_headers = {**self._common_headers}
        if self.current_csrf_token:
            authenticated_get_headers["X-CSRF-ID"] = self.current_csrf_token

        try:
            async with self.session.get(
                self._status_cgi_url,
                headers=authenticated_get_headers,
            ) as response:
                if response.status == 200:
                    try:
                        response_text = await response.text()
                        response_json = json.loads(response_text)
                        try:
                            airos_data = AirOSData.from_dict(response_json)
                        except (MissingField, InvalidFieldValue) as err:
                            logger.exception("Failed to deserialize AirOS data")
                            raise KeyDataMissingError from err

                        # Show new enums detected, once after (each) startup
                        if airos_data.warnings:
                            for field_name, messages in airos_data.warnings.items():
                                for msg in messages:
                                    log = f"AirOS data warning for field '{field_name}': {msg}"
                                    if log not in self.warnings_cache:
                                        self.warnings_cache.append(log)
                                        logger.warning(log)

                        return airos_data
                    except json.JSONDecodeError:
                        logger.exception(
                            "JSON Decode Error in authenticated status response"
                        )
                        raise DataMissingError from None
                else:
                    log = f"Authenticated status.cgi failed: {response.status}. Response: {response_text}"
                    logger.error(log)
        except (
            aiohttp.ClientError,
            aiohttp.client_exceptions.ConnectionTimeoutError,
        ) as err:
            logger.exception("Error during authenticated status.cgi call")
            raise DeviceConnectionError from err

    async def stakick(self, mac_address: str = None) -> bool:
        """Reconnect client station."""
        if not self.connected:
            logger.error("Not connected, login first")
            raise DeviceConnectionError from None
        if not mac_address:
            logger.error("Device mac-address missing")
            raise DataMissingError from None

        kick_request_headers = {**self._common_headers}
        if self.current_csrf_token:
            kick_request_headers["X-CSRF-ID"] = self.current_csrf_token

        kick_payload = {"staif": "ath0", "staid": mac_address.upper()}

        kick_request_headers["Content-Type"] = (
            "application/x-www-form-urlencoded; charset=UTF-8"
        )
        post_data = kick_payload

        try:
            async with self.session.post(
                self._stakick_cgi_url,
                headers=kick_request_headers,
                data=post_data,
            ) as response:
                if response.status == 200:
                    return True
                response_text = await response.text()
                log = f"Unable to restart connection response status {response.status} with {response_text}"
                logger.error(log)
                return False
        except (
            aiohttp.ClientError,
            aiohttp.client_exceptions.ConnectionTimeoutError,
        ) as err:
            logger.exception("Error during reconnect stakick.cgi call")
            raise DeviceConnectionError from err
