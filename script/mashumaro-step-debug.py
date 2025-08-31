"""Debug userdata json to see where things don't add up."""

import json
import logging
import os
import sys
from typing import Any

_current_script_dir = os.path.dirname(os.path.abspath(__file__))  # noqa: PTH100, PTH120
_project_root_dir = os.path.abspath(os.path.join(_current_script_dir, os.pardir))  # noqa: PTH100, PTH118

if _project_root_dir not in sys.path:
    sys.path.append(_project_root_dir)

from airos.airos6 import AirOS6  # noqa: E402
from airos.airos8 import AirOS8  # noqa: E402
from airos.data import (  # noqa: E402
    AirOS6Data,
    AirOS8Data,
    Interface,
    Interface6,
    Remote,
    Station,
    Wireless,
    Wireless6,
)

logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)
_LOGGER = logging.getLogger(__name__)


def main() -> None:
    """Debug data."""
    if len(sys.argv) <= 1:
        _LOGGER.info("Use with file to check")
        raise Exception("File to check not provided.")  # noqa: TRY002

    current_script_dir = os.path.dirname(os.path.abspath(__file__))  # noqa: PTH100, PTH120
    project_root_dir = os.path.abspath(os.path.join(current_script_dir, os.pardir))  # noqa: PTH100, PTH118

    if project_root_dir not in sys.path:
        sys.path.append(project_root_dir)

    # Load the JSON data
    with open(sys.argv[1], encoding="utf-8") as f:  # noqa: PTH123
        data = json.loads(f.read())

    fwversion = (data.get("host") or {}).get("fwversion")
    if not fwversion:
        _LOGGER.error(
            "Unable to determine firmware version in '%s' (missing host.fwversion)",
            sys.argv[1],
        )
        raise ValueError("fwversion missing") from None

    try:
        fw_major = int(fwversion.lstrip("v").split(".", 1)[0])
    except (ValueError, AttributeError) as exc:
        _LOGGER.error("Invalid firmware version '%s' in '%s'", fwversion, sys.argv[1])
        raise ValueError("invalid fwversion") from exc

    if fw_major != 8:
        _LOGGER.warning("Non firmware 8 detected: %s", fwversion)

    try:
        _LOGGER.info("Attempting to deserialize Wireless object...")
        wireless_data: dict[str, Any] = data["wireless"]

        _LOGGER.info("  -> Checking Wireless enums...")
        if fw_major == 6:
            wireless_data_prepped = Wireless6.__pre_deserialize__(wireless_data.copy())
        else:
            wireless_data_prepped = Wireless.__pre_deserialize__(wireless_data.copy())  # noqa: F841
        _LOGGER.info(
            "    Success! Wireless enums (mode, ieeemode, security) are valid."
        )

        if fw_major >= 8:
            _LOGGER.info("  -> Checking list of Station objects...")
            station_list_data = wireless_data["sta"]
            station_obj_list = []
            for i, station_data in enumerate(station_list_data):
                _LOGGER.info("    -> Checking Station object at index %s...", i)
                remote_data = station_data["remote"]
                _LOGGER.info("      -> Checking Remote object at index %s...", i)
                _LOGGER.info("Remote data = %s", remote_data)
                remote_obj = Remote.from_dict(remote_data)  # noqa: F841
                _LOGGER.info("         Success! Remote is valid.")

                station_obj = Station.from_dict(station_data)
                station_obj_list.append(station_obj)
                _LOGGER.info("      Success! Station at index %s is valid.", i)
        else:
            _LOGGER.warning("  fw lower than 8 -> no station information")

        _LOGGER.info("  -> Checking top-level Wireless object...")
        wireless_obj: Wireless | Wireless6
        if fw_major == 6:
            wireless_obj = Wireless6.from_dict(wireless_data)
        else:
            wireless_obj = Wireless.from_dict(wireless_data)  # noqa: F841
        _LOGGER.info("  -> Success! The Wireless object is valid.")

        _LOGGER.info("  -> Checking list of Interface objects...")
        interfaces = data["interfaces"]
        for i, interface_data in enumerate(interfaces):
            _LOGGER.info("    -> Checking Interface object at index %s...", i)
            _LOGGER.info("         Interface should be %s.", interface_data["ifname"])
            interface_obj: Interface | Interface6
            if fw_major == 6:
                interface_obj = Interface6.from_dict(interface_data)
            else:
                interface_obj = Interface.from_dict(interface_data)  # noqa: F841
            _LOGGER.info("         Success! Interface is valid.")

        airos_data_obj: AirOS6Data | AirOS8Data
        if fw_major == 6:
            _LOGGER.info("Deriving AirOS6Data from object...")
            derived_data = AirOS6._derived_data_helper(  # noqa: SLF001
                data, AirOS6.derived_wireless_data
            )
            _LOGGER.info("Attempting to deserialize full AirOS6Data object...")
            airos_data_obj = AirOS6Data.from_dict(derived_data)
            _LOGGER.info("Success! Full AirOS6Data object is valid.")
        else:
            _LOGGER.info("Deriving AirOS8Data from object...")
            derived_data = AirOS8._derived_data_helper(  # noqa: SLF001
                data, AirOS8.derived_wireless_data
            )
            _LOGGER.info("Attempting to deserialize full AirOS8Data object...")
            airos_data_obj = AirOS8Data.from_dict(derived_data)  # noqa: F841
            _LOGGER.info("Success! Full AirOS8Data object is valid.")

    except Exception:
        _LOGGER.info("\n------------------")
        _LOGGER.info("CRITICAL ERROR FOUND!")
        _LOGGER.exception("The program failed")
        _LOGGER.info("------------------\n")


if __name__ == "__main__":
    main()
