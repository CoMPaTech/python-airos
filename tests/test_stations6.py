"""Ubiquiti AirOS tests."""

from http.cookies import SimpleCookie
import json
import os
from typing import Any
from unittest.mock import AsyncMock, patch

import aiofiles
import pytest

from airos.airos6 import AirOS6
from airos.data import AirOS6Data


async def _read_fixture(fixture: str = "NanoStation_M5_sta_v6.3.16") -> Any:
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
    ("mode", "fixture"),
    [
        ("sta", "NanoStation_M5_sta_v6.3.16"),
    ],
)
@pytest.mark.asyncio
async def test_ap_object(
    airos6_device: AirOS6, base_url: str, mode: str, fixture: str
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
        patch.object(airos6_device, "_request_json", new=mock_request_json),
        # You need to manually set the connected state since login() is mocked
        patch.object(airos6_device, "connected", True),
    ):
        # We don't need to patch the session directly anymore
        await airos6_device.login()
        status: AirOS6Data = await airos6_device.status()

    # Assertions remain the same as they check the final result
    assert status.wireless.mode
    assert status.wireless.mode.value == mode
    assert status.derived.mac_interface == "br0"

    cookie = SimpleCookie()
    cookie["session_id"] = "test-cookie"
    cookie["AIROS_TOKEN"] = "abc123"
