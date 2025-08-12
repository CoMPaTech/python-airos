"""Ubiquity AirOS test fixtures."""

from _collections_abc import AsyncGenerator, Generator
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from airos.airos8 import AirOS
from airos.discovery import AirOSDiscoveryProtocol
import pytest

import aiohttp


@pytest.fixture
def base_url() -> str:
    """Return a testing url."""
    return "http://device.local"


@pytest.fixture
async def airos_device(base_url: str) -> AsyncGenerator[AirOS, None]:
    """AirOS device fixture."""
    session = aiohttp.ClientSession(cookie_jar=aiohttp.CookieJar())
    instance = AirOS(base_url, "username", "password", session, use_ssl=False)
    yield instance
    await session.close()


@pytest.fixture
def mock_datagram_endpoint() -> Generator[
    tuple[asyncio.DatagramTransport, AirOSDiscoveryProtocol], None, None
]:
    """Fixture to mock the creation of the UDP datagram endpoint."""
    # Define the mock objects FIRST, so they are in scope
    mock_transport = MagicMock(spec=asyncio.DatagramTransport)
    mock_protocol_instance = MagicMock(spec=AirOSDiscoveryProtocol)

    # Now, define the AsyncMock using the pre-defined variables
    mock_create_datagram_endpoint = AsyncMock(
        return_value=(mock_transport, mock_protocol_instance)
    )

    with (
        patch("asyncio.get_running_loop") as mock_get_loop,
        patch(
            "airos.discovery.AirOSDiscoveryProtocol",
            new=MagicMock(return_value=mock_protocol_instance),
        ),
    ):
        mock_loop = mock_get_loop.return_value
        mock_loop.create_datagram_endpoint = mock_create_datagram_endpoint

        yield mock_transport, mock_protocol_instance
