"""Discover Ubiquiti UISP airOS device broadcasts."""

import asyncio
from collections.abc import Callable
import logging
import socket
import struct
from typing import Any

from .exceptions import AirOSDiscoveryError, AirOSEndpointError, AirOSListenerError

_LOGGER = logging.getLogger(__name__)

DISCOVERY_PORT: int = 10002
BUFFER_SIZE: int = 1024


class AirOSDiscoveryProtocol(asyncio.DatagramProtocol):
    """A UDP protocol implementation for discovering Ubiquiti airOS devices.

    This class listens for UDP broadcast announcements from airOS devices
    on a specific port (10002) and parses the proprietary packet format
    to extract device information. It acts as the low-level listener.

    Attributes:
        callback: An asynchronous callable that will be invoked with
                  the parsed device information upon discovery.
        transport: The UDP transport layer object, set once the connection is made.

    """

    def __init__(self, callback: Callable[[dict[str, Any]], None]) -> None:
        """Initialize AirOSDiscoveryProtocol.

        Args:
            callback: An asynchronous function to call when a device is discovered.
                      It should accept a dictionary containing device information.

        """
        self.callback = callback
        self.transport: asyncio.DatagramTransport | None = None

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        """Set up the UDP socket for broadcasting and reusing the address."""
        self.transport = transport  # type: ignore[assignment] # transport is DatagramTransport
        sock: socket.socket = self.transport.get_extra_info("socket")
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        log = f"AirOS discovery listener (low-level) started on UDP port {DISCOVERY_PORT}."
        _LOGGER.debug(log)

    def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
        """Parse the received UDP packet and, if successful, schedules the callback.

        Errors during parsing are logged internally by parse_airos_packet.
        """
        host_ip: str = addr[0]
        try:
            parsed_data: dict[str, Any] | None = self.parse_airos_packet(data, host_ip)
            if parsed_data:
                # Schedule the user-provided callback, don't await to keep listener responsive
                asyncio.create_task(self.callback(parsed_data))  # noqa: RUF006
        except (AirOSEndpointError, AirOSListenerError) as err:
            # These are expected types of malformed packets. Log the specific error
            # and then re-raise as AirOSDiscoveryError.
            log = f"Parsing failed for packet from {host_ip}: {err}"
            _LOGGER.exception(log)
            raise AirOSDiscoveryError(f"Malformed packet from {host_ip}") from err
        except Exception as err:
            # General error during datagram reception (e.g., in callback itself)
            log = f"Error processing AirOS discovery packet from {host_ip}. Data hex: {data.hex()}"
            _LOGGER.exception(log)
            raise AirOSDiscoveryError from err

    def error_received(self, exc: Exception | None) -> None:
        """Handle send or receive operation raises an OSError."""
        if exc:
            log = f"UDP error received in AirOSDiscoveryProtocol: {exc}"
            _LOGGER.error(log)

    def connection_lost(self, exc: Exception | None) -> None:
        """Handle connection is lost or closed."""
        _LOGGER.debug("AirOSDiscoveryProtocol connection lost.")
        if exc:
            _LOGGER.exception("AirOSDiscoveryProtocol connection lost due to")
            raise AirOSDiscoveryError from None

    def parse_airos_packet(self, data: bytes, host_ip: str) -> dict[str, Any] | None:
        """Parse a raw airOS discovery UDP packet.

        This method extracts various pieces of information from the proprietary
        Ubiquiti airOS discovery packet format, which includes a fixed header
        followed by a series of Type-Length-Value (TLV) entries. Different
        TLV types use different length encoding schemes (fixed, 1-byte, 2-byte).

        Args:
            data: The raw byte data of the UDP packet payload.
            host_ip: The IP address of the sender, used as a fallback or initial IP.

        Returns:
            A dictionary containing parsed device information if successful,
            otherwise None. Values will be None if not found or cannot be parsed.

        """
        parsed_info: dict[str, str | int | None] = {
            "ip_address": host_ip,
            "mac_address": None,
            "hostname": None,
            "model": None,
            "firmware_version": None,
            "uptime_seconds": None,
            "ssid": None,
            "full_model_name": None,
        }

        # --- Fixed Header (6 bytes) ---
        if len(data) < 6:
            log = f"Packet too short for initial fixed header. Length: {len(data)}. Data: {data.hex()}"
            _LOGGER.debug(log)
            raise AirOSEndpointError(f"Malformed packet: {log}")

        if data[0] != 0x01 or data[1] != 0x06:
            log = f"Packet does not start with expected AirOS header (0x01 0x06). Actual: {data[0:2].hex()}"
            _LOGGER.debug(log)
            raise AirOSEndpointError(f"Malformed packet: {log}")

        offset: int = 6

        # --- Main TLV Parsing Loop ---
        try:
            while offset < len(data):
                if (len(data) - offset) < 1:
                    log = f"Not enough bytes for next TLV type. Remaining: {data[offset:].hex()}"
                    _LOGGER.debug(log)
                    break

                tlv_type: int = data[offset]
                offset += 1

                if tlv_type == 0x06:  # Device MAC Address (fixed 6-byte value)
                    expected_length: int = 6
                    if (len(data) - offset) >= expected_length:
                        mac_bytes: bytes = data[offset : offset + expected_length]
                        parsed_info["mac_address"] = ":".join(
                            f"{b:02x}" for b in mac_bytes
                        ).upper()
                        offset += expected_length
                        log = f"Parsed MAC from type 0x06: {parsed_info['mac_address']}"
                        _LOGGER.debug(log)
                    else:
                        log = f"Truncated MAC address TLV (Type 0x06). Expected {expected_length}, got {len(data) - offset} bytes. Remaining: {data[offset:].hex()}"
                        _LOGGER.warning(log)
                        log = f"Malformed packet: {log}"
                        raise AirOSEndpointError(log)

                elif tlv_type in [
                    0x02,
                    0x03,
                    0x0A,
                    0x0B,
                    0x0C,
                    0x0D,
                    0x0E,
                    0x10,
                    0x14,
                    0x18,
                ]:
                    if (len(data) - offset) < 2:
                        log = f"Truncated TLV (Type {tlv_type:#x}), no 2-byte length field. Remaining: {data[offset:].hex()}"
                        _LOGGER.warning(log)
                        log = f"Malformed packet: {log}"
                        raise AirOSEndpointError(log)

                    tlv_length: int = struct.unpack_from(">H", data, offset)[0]
                    offset += 2

                    if tlv_length > (len(data) - offset):
                        log = f"TLV type {tlv_type:#x} length {tlv_length} exceeds remaining data "
                        _LOGGER.warning(log)
                        log = f"({len(data) - offset} bytes left). Packet malformed. "
                        _LOGGER.warning(log)
                        log = f"Data from TLV start: {data[offset - 3 :].hex()}"
                        _LOGGER.warning(log)
                        log = f"Malformed packet: {log}"
                        raise AirOSEndpointError(log)

                    tlv_value: bytes = data[offset : offset + tlv_length]

                    if tlv_type == 0x02:
                        if tlv_length == 10:
                            ip_bytes: bytes = tlv_value[6:10]
                            parsed_info["ip_address"] = ".".join(map(str, ip_bytes))
                            log = f"Parsed IP from type 0x02 block: {parsed_info['ip_address']}"
                            _LOGGER.debug(log)
                        else:
                            log = f"Unexpected length for 0x02 TLV (MAC+IP). Expected 10, got {tlv_length}. Value: {tlv_value.hex()}"
                            _LOGGER.warning(log)

                    elif tlv_type == 0x03:
                        parsed_info["firmware_version"] = tlv_value.decode(
                            "ascii", errors="ignore"
                        )
                        log = f"Parsed Firmware: {parsed_info['firmware_version']}"
                        _LOGGER.debug(log)

                    elif tlv_type == 0x0A:
                        if tlv_length == 4:
                            parsed_info["uptime_seconds"] = struct.unpack(
                                ">I", tlv_value
                            )[0]
                            log = f"Parsed Uptime: {parsed_info['uptime_seconds']}s"
                            _LOGGER.debug(log)
                        else:
                            log = f"Unexpected length for Uptime (Type 0x0A): {tlv_length}. Value: {tlv_value.hex()}"
                            _LOGGER.warning(log)

                    elif tlv_type == 0x0B:
                        parsed_info["hostname"] = tlv_value.decode(
                            "utf-8", errors="ignore"
                        )
                        log = f"Parsed Hostname: {parsed_info['hostname']}"
                        _LOGGER.debug(log)

                    elif tlv_type == 0x0C:
                        parsed_info["model"] = tlv_value.decode(
                            "ascii", errors="ignore"
                        )
                        log = f"Parsed Model: {parsed_info['model']}"
                        _LOGGER.debug(log)

                    elif tlv_type == 0x0D:
                        parsed_info["ssid"] = tlv_value.decode("utf-8", errors="ignore")
                        log = f"Parsed SSID: {parsed_info['ssid']}"
                        _LOGGER.debug(log)

                    elif tlv_type == 0x14:
                        parsed_info["full_model_name"] = tlv_value.decode(
                            "utf-8", errors="ignore"
                        )
                        log = (
                            f"Parsed Full Model Name: {parsed_info['full_model_name']}"
                        )
                        _LOGGER.debug(log)

                    elif tlv_type == 0x18:
                        if tlv_length == 4 and tlv_value == b"\x00\x00\x00\x00":
                            _LOGGER.debug("Detected end marker (Type 0x18).")
                        else:
                            log = f"Unhandled TLV type: {tlv_type:#x} with length {tlv_length}. Value: {tlv_value.hex()}"
                            _LOGGER.debug(log)
                    elif tlv_type in [0x0E, 0x10]:
                        log = f"Unhandled TLV type: {tlv_type:#x} with length {tlv_length}. Value: {tlv_value.hex()}"
                        _LOGGER.debug(log)

                    offset += tlv_length

                else:
                    log = f"Unhandled TLV type: {tlv_type:#x} at offset {offset - 1}. "
                    log += f"Cannot determine length, stopping parsing. Remaining: {data[offset - 1 :].hex()}"
                    _LOGGER.warning(log)
                    log = f"Malformed packet: {log}"
                    raise AirOSEndpointError(log)

        except (struct.error, IndexError) as err:
            log = f"Parsing error (struct/index) in AirOSDiscoveryProtocol: {err} at offset {offset}. Remaining data: {data[offset:].hex()}"
            _LOGGER.debug(log)
            log = f"Malformed packet: {log}"
            raise AirOSEndpointError(log) from err
        except AirOSEndpointError:  # Catch AirOSEndpointError specifically, re-raise it
            raise
        except Exception as err:
            _LOGGER.exception("Unexpected error during AirOS packet parsing")
            raise AirOSListenerError from err

        return parsed_info


async def async_discover_devices(timeout: int) -> dict[str, dict[str, Any]]:
    """Discover unconfigured airOS devices on the network for a given timeout.

    This function sets up a listener, waits for a period, and returns
    all discovered devices.
    """
    _LOGGER.debug("Starting AirOS device discovery for %s seconds", timeout)
    discovered_devices: dict[str, dict[str, Any]] = {}

    async def _async_airos_device_found(device_info: dict[str, Any]) -> None:
        """Handle discovered device."""
        mac_address = device_info.get("mac_address")
        if mac_address:
            discovered_devices[mac_address] = device_info
            _LOGGER.debug(
                "Discovered device: %s", device_info.get("hostname", mac_address)
            )

    transport: asyncio.DatagramTransport | None = None
    try:
        (
            transport,
            protocol,
        ) = await asyncio.get_running_loop().create_datagram_endpoint(
            lambda: AirOSDiscoveryProtocol(_async_airos_device_found),
            local_addr=("0.0.0.0", DISCOVERY_PORT),
        )
        try:
            await asyncio.sleep(timeout)
        finally:
            if transport:
                _LOGGER.debug("Closing AirOS discovery listener")
                transport.close()
    except OSError as err:
        if err.errno == 98:
            _LOGGER.error("Address in use, another instance may be running.")
            raise AirOSEndpointError("address_in_use") from err
        _LOGGER.exception("Network endpoint error during discovery")
        raise AirOSEndpointError("cannot_connect") from err
    except asyncio.CancelledError as err:
        _LOGGER.warning("Discovery listener cancelled: %s", err)
        raise AirOSListenerError("cannot_connect") from err
    except Exception as err:
        _LOGGER.exception("An unexpected error occurred during discovery")
        raise AirOSListenerError("cannot_connect") from err

    return discovered_devices
