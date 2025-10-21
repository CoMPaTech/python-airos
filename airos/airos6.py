"""Ubiquiti AirOS 6."""

from __future__ import annotations

import logging
from typing import Any

from aiohttp import ClientSession

from .base import AirOS
from .data import AirOS6Data, DerivedWirelessRole
from .exceptions import AirOSNotSupportedError

_LOGGER = logging.getLogger(__name__)


class AirOS6(AirOS[AirOS6Data]):
    """AirOS 6 connection class."""

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        session: ClientSession,
        use_ssl: bool = True,
    ) -> None:
        """Initialize AirOS8 class."""
        super().__init__(
            data_model=AirOS6Data,
            host=host,
            username=username,
            password=password,
            session=session,
            use_ssl=use_ssl,
        )

    @staticmethod
    def _derived_wireless_data(
        derived: dict[str, Any], response: dict[str, Any]
    ) -> dict[str, Any]:
        """Add derived wireless data to the device response."""
        # Access Point / Station  - no info on ptp/ptmp
        # assuming ptp for station mode
        derived["ptp"] = True
        wireless_mode = response.get("wireless", {}).get("mode", "")
        match wireless_mode:
            case "ap":
                derived["access_point"] = True
                derived["role"] = DerivedWirelessRole.ACCESS_POINT
            case "sta":
                derived["station"] = True

        return derived

    async def update_check(self, force: bool = False) -> dict[str, Any]:
        """Check for firmware updates. Not supported on AirOS6."""
        raise AirOSNotSupportedError("Firmware update check not supported on AirOS6.")

    async def stakick(self, mac_address: str | None = None) -> bool:
        """Kick a station off the AP. Not supported on AirOS6."""
        raise AirOSNotSupportedError("Station kick not supported on AirOS6.")

    async def provmode(self, active: bool = False) -> bool:
        """Enable/Disable provisioning mode. Not supported on AirOS6."""
        raise AirOSNotSupportedError("Provisioning mode not supported on AirOS6.")

    async def warnings(self) -> dict[str, Any]:
        """Get device warnings. Not supported on AirOS6."""
        raise AirOSNotSupportedError("Device warnings not supported on AirOS6.")

    async def progress(self) -> dict[str, Any]:
        """Get firmware progress. Not supported on AirOS6."""
        raise AirOSNotSupportedError("Firmware progress not supported on AirOS6.")

    async def download(self) -> dict[str, Any]:
        """Download the device firmware. Not supported on AirOS6."""
        raise AirOSNotSupportedError("Firmware download not supported on AirOS6.")

    async def install(self) -> dict[str, Any]:
        """Install a firmware update. Not supported on AirOS6."""
        raise AirOSNotSupportedError("Firmware install not supported on AirOS6.")
