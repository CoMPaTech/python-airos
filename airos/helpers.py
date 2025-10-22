"""Ubiquiti AirOS firmware helpers."""

import logging
from typing import TypedDict

import aiohttp

from .airos8 import AirOS8
from .exceptions import (
    AirOSConnectionAuthenticationError,
    AirOSConnectionSetupError,
    AirOSDataMissingError,
    AirOSDeviceConnectionError,
    AirOSKeyDataMissingError,
)

_LOGGER = logging.getLogger(__name__)


class DetectDeviceData(TypedDict):
    """Container for device data."""

    fw_major: int
    mac: str
    hostname: str


async def async_get_firmware_data(
    host: str,
    username: str,
    password: str,
    session: aiohttp.ClientSession,
    use_ssl: bool = True,
) -> DetectDeviceData:
    """Connect to a device and return the major firmware version."""
    detect_device: AirOS8 = AirOS8(host, username, password, session, use_ssl)

    try:
        await detect_device.login()
        device_data = await detect_device.raw_status()
    except (
        AirOSConnectionSetupError,
        AirOSDeviceConnectionError,
    ):
        _LOGGER.exception("Error connecting to device at %s", host)
        raise
    except (AirOSConnectionAuthenticationError, AirOSDataMissingError):
        _LOGGER.exception("Authentication error connecting to device at %s", host)
        raise
    except AirOSKeyDataMissingError:
        _LOGGER.exception("Key data missing from device at %s", host)
        raise

    return {
        "fw_major": AirOS8.get_fw_major(device_data.get("host", {}).get("fwversion")),
        "hostname": device_data.get("host", {}).get("hostname"),
        "mac": AirOS8.get_mac(device_data.get("interfaces", {}))["mac"],
    }
