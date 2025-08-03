"""Provide mashumaro data object for AirOSData."""

from dataclasses import dataclass
from enum import Enum
import logging
from typing import Any

from mashumaro import DataClassDictMixin

logger = logging.getLogger(__name__)


def _check_and_log_unknown_enum_value(
    data_dict: dict[str, Any],
    key: str,
    enum_class: type[Enum],
    dataclass_name: str,
    field_name: str,
) -> None:
    """Clean unsupported parameters with logging."""
    value = data_dict.get(key)
    if value is not None and isinstance(value, str):
        if value not in [e.value for e in enum_class]:
            logger.warning(
                "Unknown value '%s' for %s.%s. Please report at "
                "https://github.com/CoMPaTech/python-airos/issues so we can add support.",
                value,
                dataclass_name,
                field_name,
            )
            del data_dict[key]


class IeeeMode(Enum):
    """Enum definition."""

    AUTO = "AUTO"
    _11ACVHT80 = "11ACVHT80"  # On a NanoStation
    _11ACVHT40 = "11ACVHT40"
    _11ACVHT20 = "11ACVHT20"  # On a LiteBeam
    # More to be added when known


class WirelessMode(Enum):
    """Enum definition."""

    PTP_ACCESSPOINT = "ap-ptp"
    PTMP_ACCESSPOINT = "ap-ptmp"
    PTP_STATION = "sta-ptp"
    # More to be added when known


class Security(Enum):
    """Enum definition."""

    WPA2 = "WPA2"
    # More to be added when known


class NetRole(Enum):
    """Enum definition."""

    BRIDGE = "bridge"
    ROUTER = "router"
    # More to be added when known


@dataclass
class ChainName:
    """Leaf definition."""

    number: int
    name: str


@dataclass
class Host:
    """Leaf definition."""

    hostname: str
    device_id: str
    uptime: int
    power_time: int
    time: str
    timestamp: int
    fwversion: str
    devmodel: str
    netrole: NetRole
    loadavg: float
    totalram: int
    freeram: int
    temperature: int
    cpuload: float
    height: int | None  # Reported none on LiteBeam 5AC

    @classmethod
    def __pre_deserialize__(cls, d: dict[str, Any]) -> dict[str, Any]:
        """Pre-deserialize hook for Host."""
        _check_and_log_unknown_enum_value(d, "netrole", NetRole, "Host", "netrole")
        return d


@dataclass
class Services:
    """Leaf definition."""

    dhcpc: bool
    dhcpd: bool
    dhcp6d_stateful: bool
    pppoe: bool
    airview: int


@dataclass
class Firewall:
    """Leaf definition."""

    iptables: bool
    ebtables: bool
    ip6tables: bool
    eb6tables: bool


@dataclass
class Throughput:
    """Leaf definition."""

    tx: int
    rx: int


@dataclass
class ServiceTime:
    """Leaf definition."""

    time: int
    link: int


@dataclass
class Polling:
    """Leaf definition."""

    cb_capacity: int
    dl_capacity: int
    ul_capacity: int
    use: int
    tx_use: int
    rx_use: int
    atpc_status: int
    fixed_frame: bool
    gps_sync: bool
    ff_cap_rep: bool


@dataclass
class Stats:
    """Leaf definition."""

    rx_bytes: int
    rx_packets: int
    rx_pps: int
    tx_bytes: int
    tx_packets: int
    tx_pps: int


@dataclass
class EvmData:
    """Leaf definition."""

    usage: int
    cinr: int
    evm: list[list[int]]


@dataclass
class Airmax:
    """Leaf definition."""

    actual_priority: int
    beam: int
    desired_priority: int
    cb_capacity: int
    dl_capacity: int
    ul_capacity: int
    atpc_status: int
    rx: EvmData
    tx: EvmData


@dataclass
class EthList:
    """Leaf definition."""

    ifname: str
    enabled: bool
    plugged: bool
    duplex: bool
    speed: int
    snr: list[int]
    cable_len: int


@dataclass
class GPSData:
    """Leaf definition."""

    lat: str
    lon: str
    fix: int


@dataclass
class UnmsStatus:
    """Leaf definition."""

    status: int
    timestamp: str | None = None


@dataclass
class Remote:
    """Leaf definition."""

    age: int
    device_id: str
    hostname: str
    platform: str
    version: str
    time: str
    cpuload: float
    temperature: int
    totalram: int
    freeram: int
    netrole: str
    mode: WirelessMode
    sys_id: str
    tx_throughput: int
    rx_throughput: int
    uptime: int
    power_time: int
    compat_11n: int
    signal: int
    rssi: int
    noisefloor: int
    tx_power: int
    distance: int
    rx_chainmask: int
    chainrssi: list[int]
    tx_ratedata: list[int]
    tx_bytes: int
    rx_bytes: int
    antenna_gain: int
    cable_loss: int
    height: int
    ethlist: list[EthList]
    ipaddr: list[str]
    ip6addr: list[str]
    gps: GPSData
    oob: bool
    unms: UnmsStatus
    airview: int
    service: ServiceTime

    @classmethod
    def __pre_deserialize__(cls, d: dict[str, Any]) -> dict[str, Any]:
        """Pre-deserialize hook for Wireless."""
        _check_and_log_unknown_enum_value(d, "mode", WirelessMode, "Wireless", "mode")
        return d


@dataclass
class Disconnected:
    """Leaf definition for disconnected devices."""

    mac: str
    lastip: str
    signal: int
    hostname: str
    platform: str
    reason_code: int
    disconnect_duration: int
    airos_connected: bool = False  # Mock add to determine Disconnected vs Station


@dataclass
class Station:
    """Leaf definition for connected/active devices."""

    mac: str
    lastip: str
    signal: int
    rssi: int
    noisefloor: int
    chainrssi: list[int]
    tx_idx: int
    rx_idx: int
    tx_nss: int
    rx_nss: int
    tx_latency: int
    distance: int
    tx_packets: int
    tx_lretries: int
    tx_sretries: int
    uptime: int
    dl_signal_expect: int
    ul_signal_expect: int
    cb_capacity_expect: int
    dl_capacity_expect: int
    ul_capacity_expect: int
    dl_rate_expect: int
    ul_rate_expect: int
    dl_linkscore: int
    ul_linkscore: int
    dl_avg_linkscore: int
    ul_avg_linkscore: int
    tx_ratedata: list[int]
    stats: Stats
    airmax: Airmax
    last_disc: int
    remote: Remote
    airos_connected: bool = True  # Mock add to determine Disconnected vs Station


@dataclass
class Wireless:
    """Leaf definition."""

    essid: str
    mode: WirelessMode
    ieeemode: IeeeMode
    band: int
    compat_11n: int
    hide_essid: int
    apmac: str
    antenna_gain: int
    frequency: int
    center1_freq: int
    dfs: int
    distance: int
    security: Security
    noisef: int
    txpower: int
    aprepeater: bool
    rstatus: int
    chanbw: int
    rx_chainmask: int
    tx_chainmask: int
    nol_state: int
    nol_timeout: int
    cac_state: int
    cac_timeout: int
    rx_idx: int
    rx_nss: int
    tx_idx: int
    tx_nss: int
    throughput: Throughput
    service: ServiceTime
    polling: Polling
    count: int
    sta: list[Station]
    sta_disconnected: list[Disconnected]

    @classmethod
    def __pre_deserialize__(cls, d: dict[str, Any]) -> dict[str, Any]:
        """Pre-deserialize hook for Wireless."""
        _check_and_log_unknown_enum_value(d, "mode", WirelessMode, "Wireless", "mode")
        _check_and_log_unknown_enum_value(
            d, "ieeemode", IeeeMode, "Wireless", "ieeemode"
        )
        _check_and_log_unknown_enum_value(
            d, "security", Security, "Wireless", "security"
        )
        return d


@dataclass
class InterfaceStatus:
    """Leaf definition."""

    plugged: bool
    tx_bytes: int
    rx_bytes: int
    tx_packets: int
    rx_packets: int
    tx_errors: int
    rx_errors: int
    tx_dropped: int
    rx_dropped: int
    ipaddr: str
    speed: int
    duplex: bool
    snr: list[int] | None = None
    cable_len: int | None = None
    ip6addr: list[dict[str, Any]] | None = None


@dataclass
class Interface:
    """Leaf definition."""

    ifname: str
    hwaddr: str
    enabled: bool
    mtu: int
    status: InterfaceStatus


@dataclass
class ProvisioningMode:
    """Leaf definition."""

    pass


@dataclass
class NtpClient:
    """Leaf definition."""

    pass


@dataclass
class GPSMain:
    """Leaf definition."""

    lat: float
    lon: float
    fix: int


@dataclass
class Derived:
    """Contain custom data generated by this module."""

    mac: str  # Base device MAC address (i.e. eth0)
    mac_interface: str  # Interface derived from


@dataclass
class AirOS8Data(DataClassDictMixin):
    """Dataclass for AirOS v8 devices."""

    chain_names: list[ChainName]
    host: Host
    genuine: str
    services: Services
    firewall: Firewall
    portfw: bool
    wireless: Wireless
    interfaces: list[Interface]
    provmode: Any
    ntpclient: Any
    unms: UnmsStatus
    gps: GPSMain
    derived: Derived
