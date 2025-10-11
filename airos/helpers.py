"""Ubiquiti AirOS firmware helpers."""

from typing import TypedDict

import aiohttp

from .airos6 import AirOS6
from .airos8 import AirOS8
from .exceptions import AirOSKeyDataMissingError


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
    detect: AirOS8 = AirOS8(host, username, password, session, use_ssl)

    await detect.login()
    raw_status = await detect._request_json(  # noqa: SLF001
        "GET",
        detect._status_cgi_url,  # noqa: SLF001
        authenticated=True,
    )

    fw_version = (raw_status.get("host") or {}).get("fwversion")
    if not fw_version:
        raise AirOSKeyDataMissingError("Missing host.fwversion in API response")

    try:
        fw_major = int(fw_version.lstrip("v").split(".", 1)[0])
    except (ValueError, AttributeError) as exc:
        raise AirOSKeyDataMissingError(
            f"Invalid firmware version '{fw_version}'"
        ) from exc

    if fw_major == 6:
        derived_data = AirOS6._derived_data_helper(  # noqa: SLF001
            raw_status, AirOS6.derived_wireless_data
        )
    else:  # Assume AirOS 8 for all other versions
        derived_data = AirOS8._derived_data_helper(  # noqa: SLF001
            raw_status, AirOS8.derived_wireless_data
        )

    # Extract MAC address and hostname from the derived data
    hostname = derived_data.get("host", {}).get("hostname")
    mac = derived_data.get("derived", {}).get("mac")

    if not hostname:  # pragma: no cover
        raise AirOSKeyDataMissingError("Missing hostname")

    if not mac:  # pragma: no cover
        raise AirOSKeyDataMissingError("Missing MAC address")

    return {
        "fw_major": fw_major,
        "mac": mac,
        "hostname": hostname,
    }
