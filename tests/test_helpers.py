"""Test helpers for Ubiquiti airOS devices."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from airos.airos8 import AirOS8
from airos.exceptions import AirOSKeyDataMissingError
from airos.helpers import DetectDeviceData, async_get_firmware_data

# pylint: disable=redefined-outer-name


@pytest.fixture
def mock_session() -> MagicMock:
    """Return a mock aiohttp ClientSession."""
    return MagicMock(spec=aiohttp.ClientSession)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    (
        "mock_response",
        "expected_fw_major",
        "expected_mac",
        "expected_hostname",
        "expected_exception",
    ),
    [
        # Success case for AirOS 8
        (
            {
                "host": {"fwversion": "v8.7.4", "hostname": "test-host-8"},
                "interfaces": [
                    {"hwaddr": "AA:BB:CC:DD:EE:FF", "ifname": "br0", "enabled": True}
                ],
            },
            8,
            "AA:BB:CC:DD:EE:FF",
            "test-host-8",
            None,
        ),
        # Success case for AirOS 6
        (
            {
                "host": {"fwversion": "v6.3.16", "hostname": "test-host-6"},
                "wireless": {"mode": "sta", "apmac": "11:22:33:44:55:66"},
                "interfaces": [
                    {"hwaddr": "11:22:33:44:55:66", "ifname": "br0", "enabled": True}
                ],
            },
            6,
            "11:22:33:44:55:66",
            "test-host-6",
            None,
        ),
        # Failure case: Missing host key
        ({"wireless": {}}, 0, "", "", AirOSKeyDataMissingError),
        # Failure case: Missing fwversion key
        (
            {"host": {"hostname": "test-host"}, "interfaces": []},
            0,
            "",
            "",
            AirOSKeyDataMissingError,
        ),
        # Failure case: Invalid fwversion value
        (
            {
                "host": {"fwversion": "not-a-number", "hostname": "test-host"},
                "interfaces": [],
            },
            0,
            "",
            "",
            AirOSKeyDataMissingError,
        ),
        # Failure case: Missing hostname key
        (
            {"host": {"fwversion": "v8.7.4"}, "interfaces": []},
            0,
            "",
            "",
            AirOSKeyDataMissingError,
        ),
        # Failure case: Missing MAC address
        (
            {"host": {"fwversion": "v8.7.4", "hostname": "test-host"}},
            0,
            "",
            "",
            AirOSKeyDataMissingError,
        ),
    ],
)
async def test_firmware_detection(
    mock_session: aiohttp.ClientSession,
    mock_response: dict[str, Any],
    expected_fw_major: int,
    expected_mac: str,
    expected_hostname: str,
    expected_exception: Any,
) -> None:
    """Test helper firmware detection."""

    mock_request_json = AsyncMock(
        side_effect=[
            {},  # First call for login()
            mock_response,  # Second call for the status() endpoint
        ]
    )

    with patch.object(AirOS8, "_request_json", new=mock_request_json):
        if expected_exception:
            with pytest.raises(expected_exception):
                await async_get_firmware_data(
                    host="192.168.1.3",
                    username="testuser",
                    password="testpassword",
                    session=mock_session,
                    use_ssl=True,
                )
        else:
            # Test the success case
            device_data: DetectDeviceData = await async_get_firmware_data(
                host="192.168.1.3",
                username="testuser",
                password="testpassword",
                session=mock_session,
                use_ssl=True,
            )

            assert device_data["fw_major"] == expected_fw_major
            assert device_data["mac"] == expected_mac
            assert device_data["hostname"] == expected_hostname
