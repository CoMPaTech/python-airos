"""Debug userdata json to see where things don't add up."""

import json
import logging
import os
import sys
from typing import Any

current_script_dir = os.path.dirname(os.path.abspath(__file__))
project_root_dir = os.path.abspath(os.path.join(current_script_dir, os.pardir))

if project_root_dir not in sys.path:
    sys.path.append(project_root_dir)

from airos.data import AirOS8Data, Remote, Station, Wireless  # noqa: E402

logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)
_LOGGER = logging.getLogger(__name__)


def main() -> None:
    """Debug data."""
    if len(sys.argv) <= 1:
        _LOGGER.info("Use with file to check")
        raise Exception("File to check not provided.")

    current_script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root_dir = os.path.abspath(os.path.join(current_script_dir, os.pardir))

    if project_root_dir not in sys.path:
        sys.path.append(project_root_dir)

    # Load the JSON data
    with open(sys.argv[1]) as f:
        data = json.loads(f.read())

    try:
        _LOGGER.info("Attempting to deserialize Wireless object...")
        wireless_data: dict[str, Any] = data["wireless"]

        _LOGGER.info("  -> Checking Wireless enums...")
        wireless_data_prepped = Wireless.__pre_deserialize__(wireless_data.copy())  # noqa: F841
        _LOGGER.info(
            "    Success! Wireless enums (mode, ieeemode, security) are valid."
        )

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
            station_obj_list.append(station_obj)  # noqa: F841
            _LOGGER.info("      Success! Station at index %s is valid.", i)

        _LOGGER.info("  -> Checking top-level Wireless object...")
        wireless_obj = Wireless.from_dict(wireless_data)  # noqa: F841
        _LOGGER.info("  -> Success! The Wireless object is valid.")

        _LOGGER.info("Attempting to deserialize full AirOS8Data object...")
        airos_data_obj = AirOS8Data.from_dict(data)  # noqa: F841
        _LOGGER.info("Success! Full AirOS8Data object is valid.")

    except Exception as e:
        _LOGGER.info("\n------------------")
        _LOGGER.info("CRITICAL ERROR FOUND!")
        _LOGGER.info("The program failed at: %s", e)
        _LOGGER.info("------------------\n")


if __name__ == "__main__":
    main()
