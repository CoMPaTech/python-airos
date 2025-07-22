"""Provide mashumaro data object for AirOSData."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from mashumaro import DataClassDictMixin


class IeeeMode(Enum):
    """Enum definition."""

    AUTO = "AUTO"
    _11ACVHT80 = "11ACVHT80"
    # More to be added when known


class WirelessMode(Enum):
    """Enum definition."""

    AccessPoint_PointToPoint = "ap-ptp"
    Station_PointToPoint = "sta-ptp"
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
    netrole: NetRole | str
    loadavg: float
    totalram: int
    freeram: int
    temperature: int
    cpuload: float
    height: int


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
    mode: WirelessMode | str  # Allow non-breaking future expansion
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
    unms: dict[str, Any]
    airview: int
    service: ServiceTime


@dataclass
class Station:
    """Leaf definition."""

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


@dataclass
class Wireless:
    """Leaf definition."""

    essid: str
    mode: WirelessMode | str  # Allow non-breaking expansion
    ieeemode: IeeeMode | str  # Allow non-breaking expansion
    band: int
    compat_11n: int
    hide_essid: int
    apmac: str
    antenna_gain: int
    frequency: int
    center1_freq: int
    dfs: int
    distance: int
    security: Security | str  # Allow non-breaking expansion
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
    sta_disconnected: list[Any]


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
class UnmsStatus:
    """Leaf definition."""

    status: int


@dataclass
class GPSMain:
    """Leaf definition."""

    lat: float
    lon: float
    fix: int


@dataclass
class AirOSData(DataClassDictMixin):
    """Dataclass for AirOS devices."""

    chain_names: list[ChainName]
    host: Host
    genuine: str
    services: Services
    firewall: Firewall
    portfw: bool
    wireless: Wireless
    interfaces: list[Interface]
    provmode: (
        ProvisioningMode | str | dict[str, Any] | list[Any] | Any
    )  # If it can be populated, define its fields
    ntpclient: (
        NtpClient | str | dict[str, Any] | list[Any] | Any
    )  # If it can be populated, define its fields
    unms: UnmsStatus
    gps: GPSMain
    warnings: dict[str, list[str]] = field(default_factory=dict, init=False)

    @classmethod
    def __post_deserialize__(cls, airos_object: "AirOSData") -> "AirOSData":
        """Validate after deserialization."""
        airos_object.check_for_warnings()
        return airos_object

    def check_for_warnings(self):
        """Validate unions for unknown fields."""
        # Check wireless mode
        if isinstance(self.wireless.mode, str):
            self.add_warning(
                "wireless", f"Unknown (new) wireless mode: '{self.wireless.mode}'"
            )

        # Check host netrole
        if isinstance(self.host.netrole, str):
            self.add_warning(
                "host", f"Unknown (new) network role: '{self.host.netrole}'"
            )

        # Check wireless IEEE mode
        if isinstance(self.wireless.ieeemode, str):
            self.add_warning(
                "wireless", f"Unknown (new) IEEE mode: '{self.wireless.ieeemode}'"
            )

        # Check wireless security
        if isinstance(self.wireless.security, str):
            self.add_warning(
                "wireless", f"Unknown (new) security type: '{self.wireless.security}'"
            )
        # Check station remote modes
        for i, station in enumerate(self.wireless.sta):
            if hasattr(station.remote, "mode") and isinstance(station.remote.mode, str):
                self.add_warning(
                    f"wireless.sta[{i}].remote",
                    f"Unknown (new) remote mode: '{station.remote.mode}', please report to the CODEOWNERS for inclusion",
                )

    def add_warning(self, field_name: str, message: str):
        """Insert warnings into the dictionary on unknown field data."""
        if field_name not in self.warnings:
            self.warnings[field_name] = []
        self.warnings[field_name].append(message)
