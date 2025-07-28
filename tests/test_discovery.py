"""Test discovery of Ubiquiti airOS devices."""

import asyncio
import os
import socket  # Add this import
from unittest.mock import AsyncMock, MagicMock, patch

from airos.discovery import DISCOVERY_PORT, AirosDiscoveryProtocol
from airos.exceptions import AirosDiscoveryError, AirosEndpointError
import pytest


# Helper to load binary fixture
async def _read_binary_fixture(fixture_name: str) -> bytes:
    """Read a binary fixture file."""
    fixture_dir = os.path.join(os.path.dirname(__file__), "../fixtures")
    path = os.path.join(fixture_dir, fixture_name)
    try:

        def _read_file():
            with open(path, "rb") as f:
                return f.read()

        return await asyncio.to_thread(_read_file)
    except FileNotFoundError:
        pytest.fail(f"Fixture file not found: {path}")
    except Exception as e:
        pytest.fail(f"Error reading fixture file {path}: {e}")


@pytest.fixture
async def mock_airos_packet() -> bytes:
    """Fixture for a valid airos discovery packet with scrubbed data."""
    return await _read_binary_fixture("airos_sta_discovery_packet.bin")


@pytest.mark.asyncio
async def test_parse_airos_packet_success(mock_airos_packet):
    """Test parse_airos_packet with a valid packet containing scrubbed data."""
    protocol = AirosDiscoveryProtocol(
        AsyncMock()
    )  # Callback won't be called directly in this unit test
    host_ip = (
        "192.168.1.3"  # The IP address from the packet sender (as per scrubbed data)
    )

    # Directly call the parsing method
    parsed_data = protocol.parse_airos_packet(mock_airos_packet, host_ip)

    assert parsed_data is not None
    assert parsed_data["ip_address"] == "192.168.1.3"
    assert parsed_data["mac_address"] == "01:23:45:67:89:CD"  # Expected scrubbed MAC
    assert parsed_data["hostname"] == "name"  # Expected scrubbed hostname
    assert parsed_data["model"] == "NanoStation 5AC loco"
    assert parsed_data["firmware_version"] == "WA.V8.7.17"
    assert parsed_data["uptime_seconds"] == 265375
    assert parsed_data["ssid"] == "DemoSSID"
    assert parsed_data["full_model_name"] == "NanoStation 5AC loco"


@pytest.mark.asyncio
async def test_parse_airos_packet_invalid_header():
    """Test parse_airos_packet with an invalid header."""
    protocol = AirosDiscoveryProtocol(AsyncMock())
    invalid_data = b"\x00\x00\x00\x00\x00\x00" + b"someotherdata"
    host_ip = "192.168.1.100"

    # Patch the _LOGGER.debug to verify the log message
    with patch("airos.discovery._LOGGER.debug") as mock_log_debug:
        with pytest.raises(AirosEndpointError):
            protocol.parse_airos_packet(invalid_data, host_ip)
        mock_log_debug.assert_called_once()
        assert (
            "does not start with expected Airos header"
            in mock_log_debug.call_args[0][0]
        )


@pytest.mark.asyncio
async def test_parse_airos_packet_too_short():
    """Test parse_airos_packet with data too short for header."""
    protocol = AirosDiscoveryProtocol(AsyncMock())
    too_short_data = b"\x01\x06\x00"
    host_ip = "192.168.1.100"

    # Patch the _LOGGER.debug to verify the log message
    with patch("airos.discovery._LOGGER.debug") as mock_log_debug:
        with pytest.raises(AirosEndpointError):
            protocol.parse_airos_packet(too_short_data, host_ip)
        mock_log_debug.assert_called_once()
        assert (
            "Packet too short for initial fixed header"
            in mock_log_debug.call_args[0][0]
        )


@pytest.mark.asyncio
async def test_parse_airos_packet_truncated_tlv():
    """Test parse_airos_packet with a truncated TLV."""
    protocol = AirosDiscoveryProtocol(AsyncMock())
    # Header + MAC TLV (valid) + then a truncated TLV_IP
    truncated_data = (
        b"\x01\x06\x00\x00\x00\x00"  # Header
        + b"\x06"
        + bytes.fromhex("0123456789CD")  # Valid MAC (scrubbed)
        + b"\x02\x00"  # TLV type 0x02, followed by only 1 byte for length (should be 2)
    )
    host_ip = "192.168.1.100"

    # Expect AirosEndpointError due to struct.error or IndexError
    with pytest.raises(AirosEndpointError):
        protocol.parse_airos_packet(truncated_data, host_ip)


@pytest.mark.asyncio
async def test_datagram_received_calls_callback(mock_airos_packet):
    """Test that datagram_received correctly calls the callback."""
    mock_callback = AsyncMock()
    protocol = AirosDiscoveryProtocol(mock_callback)
    host_ip = "192.168.1.3"  # Sender IP

    with patch("asyncio.create_task") as mock_create_task:
        protocol.datagram_received(mock_airos_packet, (host_ip, DISCOVERY_PORT))

        # Verify the task was created and get the coroutine
        mock_create_task.assert_called_once()
        task_coro = mock_create_task.call_args[0][0]

        # Manually await the coroutine to test the callback
        await task_coro

    mock_callback.assert_called_once()
    called_args, _ = mock_callback.call_args
    parsed_data = called_args[0]
    assert parsed_data["ip_address"] == "192.168.1.3"
    assert parsed_data["mac_address"] == "01:23:45:67:89:CD"  # Verify scrubbed MAC


@pytest.mark.asyncio
async def test_datagram_received_handles_parsing_error():
    """Test datagram_received handles exceptions during parsing."""
    mock_callback = AsyncMock()
    protocol = AirosDiscoveryProtocol(mock_callback)
    invalid_data = b"\x00\x00"  # Too short, will cause parsing error
    host_ip = "192.168.1.100"

    with patch("airos.discovery._LOGGER.exception") as mock_log_exception:
        # datagram_received catches errors internally and re-raises AirosDiscoveryError
        with pytest.raises(AirosDiscoveryError):
            protocol.datagram_received(invalid_data, (host_ip, DISCOVERY_PORT))
        mock_callback.assert_not_called()
        mock_log_exception.assert_called_once()  # Ensure exception is logged


@pytest.mark.asyncio
async def test_connection_made_sets_transport():
    """Test connection_made sets up transport and socket options."""
    protocol = AirosDiscoveryProtocol(AsyncMock())
    mock_transport = MagicMock(spec=asyncio.DatagramTransport)
    mock_sock = MagicMock(spec=socket.socket)  # Corrected: socket import added
    mock_transport.get_extra_info.return_value = mock_sock

    with patch("airos.discovery._LOGGER.debug") as mock_log_debug:
        protocol.connection_made(mock_transport)

        assert protocol.transport is mock_transport
        mock_sock.setsockopt.assert_any_call(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        mock_sock.setsockopt.assert_any_call(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        mock_log_debug.assert_called_once()


@pytest.mark.asyncio
async def test_connection_lost_without_exception():
    """Test connection_lost without an exception."""
    protocol = AirosDiscoveryProtocol(AsyncMock())
    with patch("airos.discovery._LOGGER.debug") as mock_log_debug:
        protocol.connection_lost(None)
        mock_log_debug.assert_called_once_with(
            "AirosDiscoveryProtocol connection lost."
        )


@pytest.mark.asyncio
async def test_connection_lost_with_exception():
    """Test connection_lost with an exception."""
    protocol = AirosDiscoveryProtocol(AsyncMock())
    test_exception = Exception("Test connection lost error")
    with (
        patch("airos.discovery._LOGGER.exception") as mock_log_exception,
        pytest.raises(
            AirosDiscoveryError
        ),  # connection_lost now re-raises AirosDiscoveryError
    ):
        protocol.connection_lost(test_exception)
    mock_log_exception.assert_called_once()


@pytest.mark.asyncio
async def test_error_received():
    """Test error_received logs the error."""
    protocol = AirosDiscoveryProtocol(AsyncMock())
    test_exception = Exception("Test network error")
    with patch("airos.discovery._LOGGER.error") as mock_log_error:
        protocol.error_received(test_exception)
        mock_log_error.assert_called_once_with(
            f"UDP error received in AirosDiscoveryProtocol: {test_exception}"
        )
