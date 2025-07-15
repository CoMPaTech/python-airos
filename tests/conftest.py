"""Ubiquity AirOS test fixtures."""

from airos.airos8 import AirOS
import pytest

import aiohttp


@pytest.fixture
def base_url():
    """Return a testing url."""
    return "http://device.local"


@pytest.fixture
async def airos_device(base_url):
    """AirOS device fixture."""
    session = aiohttp.ClientSession(cookie_jar=aiohttp.CookieJar())
    instance = AirOS(base_url, "username", "password", session, use_ssl=False)
    yield instance
    await session.close()
