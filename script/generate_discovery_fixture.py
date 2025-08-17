"""Generate mock discovery packet for testing."""

import logging
import os
import socket
import struct

_LOGGER = logging.getLogger(__name__)

# Define the path to save the fixture
fixture_dir = os.path.join(os.path.dirname(__file__), "../fixtures")  # noqa: PTH118, PTH120
os.makedirs(fixture_dir, exist_ok=True)  # Ensure the directory exists  # noqa: PTH103
fixture_path = os.path.join(fixture_dir, "airos_sta_discovery_packet.bin")  # noqa: PTH118

# Header: 0x01 0x06 (2 bytes) + 4 reserved bytes = 6 bytes
HEADER = b"\x01\x06\x00\x00\x00\x00"

# --- Scrubbed Values ---
SCRUBBED_MAC = "01:23:45:67:89:CD"
SCRUBBED_MAC_BYTES = bytes.fromhex(SCRUBBED_MAC.replace(":", ""))
SCRUBBED_IP = "192.168.1.3"
SCRUBBED_IP_BYTES = socket.inet_aton(SCRUBBED_IP)
SCRUBBED_HOSTNAME = "name"
SCRUBBED_HOSTNAME_BYTES = SCRUBBED_HOSTNAME.encode("utf-8")

# --- Values from provided "schuur" JSON (not scrubbed) ---
FIRMWARE_VERSION = "WA.V8.7.17"
FIRMWARE_VERSION_BYTES = FIRMWARE_VERSION.encode("ascii")
UPTIME_SECONDS = 265375
MODEL = "NanoStation 5AC loco"
MODEL_BYTES = MODEL.encode("ascii")
SSID = "DemoSSID"
SSID_BYTES = SSID.encode("utf-8")
FULL_MODEL_NAME = (
    "NanoStation 5AC loco"  # Using the same as Model, as is often the case
)
FULL_MODEL_NAME_BYTES = FULL_MODEL_NAME.encode("utf-8")

# TLV Type 0x06: MAC Address (fixed 6-byte value)
TLV_MAC_TYPE = b"\x06"
TLV_MAC = TLV_MAC_TYPE + SCRUBBED_MAC_BYTES

# TLV Type 0x02: MAC + IP Address (10 bytes value, with 2-byte length field)
# Value contains first 6 bytes often MAC, last 4 bytes IP
TLV_IP_TYPE = b"\x02"
TLV_IP_VALUE = (
    SCRUBBED_MAC_BYTES + SCRUBBED_IP_BYTES
)  # 6 bytes MAC + 4 bytes IP = 10 bytes
TLV_IP_LENGTH = len(TLV_IP_VALUE).to_bytes(2, "big")
TLV_IP = TLV_IP_TYPE + TLV_IP_LENGTH + TLV_IP_VALUE

# TLV Type 0x03: Firmware Version (variable length string)
TLV_FW_TYPE = b"\x03"
TLV_FW_LENGTH = len(FIRMWARE_VERSION_BYTES).to_bytes(2, "big")
TLV_FW = TLV_FW_TYPE + TLV_FW_LENGTH + FIRMWARE_VERSION_BYTES

# TLV Type 0x0A: Uptime (4-byte integer)
TLV_UPTIME_TYPE = b"\x0a"
TLV_UPTIME_VALUE = struct.pack(">I", UPTIME_SECONDS)  # Unsigned int, big-endian
TLV_UPTIME_LENGTH = len(TLV_UPTIME_VALUE).to_bytes(2, "big")
TLV_UPTIME = TLV_UPTIME_TYPE + TLV_UPTIME_LENGTH + TLV_UPTIME_VALUE

# TLV Type 0x0B: Hostname (variable length string)
TLV_HOSTNAME_TYPE = b"\x0b"
TLV_HOSTNAME_LENGTH = len(SCRUBBED_HOSTNAME_BYTES).to_bytes(2, "big")
TLV_HOSTNAME = TLV_HOSTNAME_TYPE + TLV_HOSTNAME_LENGTH + SCRUBBED_HOSTNAME_BYTES

# TLV Type 0x0C: Model (variable length string)
TLV_MODEL_TYPE = b"\x0c"
TLV_MODEL_LENGTH = len(MODEL_BYTES).to_bytes(2, "big")
TLV_MODEL = TLV_MODEL_TYPE + TLV_MODEL_LENGTH + MODEL_BYTES

# TLV Type 0x0D: SSID (variable length string)
TLV_SSID_TYPE = b"\x0d"
TLV_SSID_LENGTH = len(SSID_BYTES).to_bytes(2, "big")
TLV_SSID = TLV_SSID_TYPE + TLV_SSID_LENGTH + SSID_BYTES

# TLV Type 0x14: Full Model Name (variable length string)
TLV_FULL_MODEL_TYPE = b"\x14"
TLV_FULL_MODEL_LENGTH = len(FULL_MODEL_NAME_BYTES).to_bytes(2, "big")
TLV_FULL_MODEL = TLV_FULL_MODEL_TYPE + TLV_FULL_MODEL_LENGTH + FULL_MODEL_NAME_BYTES

# Combine all parts
FULL_PACKET = (
    HEADER
    + TLV_MAC
    + TLV_IP
    + TLV_FW
    + TLV_UPTIME
    + TLV_HOSTNAME
    + TLV_MODEL
    + TLV_SSID
    + TLV_FULL_MODEL
)

# Write the actual binary file
with open(fixture_path, "wb") as f:  # noqa: PTH123
    f.write(FULL_PACKET)

log = f"Generated discovery packet fixture at: {fixture_path}"
log += f"Packet length: {len(FULL_PACKET)} bytes"
log += f"Packet hex: {FULL_PACKET.hex()}"
_LOGGER.info(log)
