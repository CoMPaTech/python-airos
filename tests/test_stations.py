"""Ubiquiti AirOS8 tests."""

from http.cookies import SimpleCookie
import json
import os
from typing import Any
from unittest.mock import AsyncMock, patch

import aiofiles
import pytest

from airos.airos8 import AirOS8
from airos.data import AirOS8Data


async def _read_fixture(fixture: str = "loco5ac_ap-ptp") -> Any:
    """Read fixture file per device type."""
    fixture_dir = os.path.join(os.path.dirname(__file__), "..", "fixtures", "userdata")
    path = os.path.join(fixture_dir, f"{fixture}.json")
    try:
        async with aiofiles.open(path, encoding="utf-8") as f:
            return json.loads(await f.read())
    except FileNotFoundError:
        pytest.fail(f"Fixture file not found: {path}")
    except json.JSONDecodeError as e:
        pytest.fail(f"Invalid JSON in fixture file {path}: {e}")


@pytest.mark.parametrize(
    ("mode", "fixture", "sku"),
    [
        ("ap-ptp", "loco5ac_ap-ptp", "Loco5AC"),
        ("ap-ptp", "nanostation_ap-ptp_8718_missing_gps", "Loco5AC"),
        ("sta-ptp", "loco5ac_sta-ptp", "Loco5AC"),
        ("sta-ptmp", "mocked_sta-ptmp", "UNKNOWN"),
        ("ap-ptmp", "liteapgps_ap_ptmp_40mhz", "LAP-GPS"),
        ("sta-ptmp", "nanobeam5ac_sta_ptmp_40mhz", "NBE-5AC-GEN2"),
        ("ap-ptmp", "NanoBeam_5AC_ap-ptmp_v8.7.18", "NBE-5AC-GEN2"),
    ],
)
@pytest.mark.asyncio
async def test_ap_object(
    airos8_device: AirOS8, base_url: str, mode: str, fixture: str, sku: str
) -> None:
    """Test device operation using the new _request_json method."""
    fixture_data = await _read_fixture(fixture)

    # Create an async mock that can return different values for different calls
    mock_request_json = AsyncMock(
        side_effect=[
            {},  # First call for login()
            fixture_data,  # Second call for status()
        ]
    )

    with (
        # Patch the internal method, not the session object
        patch.object(airos8_device, "_request_json", new=mock_request_json),
        # You need to manually set the connected state since login() is mocked
        patch.object(airos8_device, "connected", True),
    ):
        # We don't need to patch the session directly anymore
        await airos8_device.login()
        status: AirOS8Data = await airos8_device.status()

    # Assertions remain the same as they check the final result
    assert status.wireless.mode
    assert status.wireless.mode.value == mode
    assert status.derived.sku == sku
    assert status.derived.mac_interface == "br0"

    cookie = SimpleCookie()
    cookie["session_id"] = "test-cookie"
    cookie["AIROS_TOKEN"] = "abc123"
