"""Generate mock airos fixtures for testing."""

import inspect
import json
import logging
import os
import sys

_LOGGER = logging.getLogger(__name__)

current_script_dir = os.path.dirname(os.path.abspath(__file__))  # noqa: PTH100, PTH120
project_root_dir = os.path.abspath(os.path.join(current_script_dir, os.pardir))  # noqa: PTH100, PTH118

if project_root_dir not in sys.path:
    sys.path.append(project_root_dir)

# NOTE: This assumes the airos module is correctly installed or available in the project path.
# If not, you might need to adjust the import statement.
from airos.airos6 import AirOS6  # noqa: E402
from airos.airos8 import AirOS as AirOS8  # noqa: E402
from airos.data import AirOS6Data, AirOS8Data  # noqa: E402


def generate_airos_fixtures() -> None:
    """Process all (intended) JSON files from the userdata directory to potential fixtures."""
    print(f"Loading AirOS6 from: {inspect.getfile(AirOS6)}")

    # Define the paths to the directories
    fixture_dir = os.path.join(os.path.dirname(__file__), "../fixtures")  # noqa: PTH118, PTH120
    userdata_dir = os.path.join(os.path.dirname(__file__), "../fixtures/userdata")  # noqa: PTH118, PTH120

    # Ensure the fixture directory exists
    os.makedirs(fixture_dir, exist_ok=True)  # noqa: PTH103

    # Iterate over all files in the userdata_dir
    for filename in os.listdir(userdata_dir):  # noqa: PTH208
        if "mocked" in filename:
            continue
        if filename.endswith(".json"):
            # Construct the full paths for the base and new fixtures
            base_fixture_path = os.path.join(userdata_dir, filename)  # noqa: PTH118
            new_filename = f"airos_{filename}"
            new_fixture_path = os.path.join(fixture_dir, new_filename)  # noqa: PTH118

            _LOGGER.info("Processing '%s'...", filename)

            try:
                with open(base_fixture_path, encoding="utf-8") as source:  # noqa: PTH123
                    source_data = json.loads(source.read())

                fwversion = source_data.get("host").get("fwversion")
                if not fwversion:
                    _LOGGER.error("Unable to determine firmware version")
                    raise Exception from None  # noqa: TRY002, TRY301

                fw_major = int(fwversion.lstrip("v").split(".")[0])

                new_data: AirOS6Data | AirOS8Data

                if fw_major == 6:
                    derived_data = AirOS6._derived_data_helper(  # noqa: SLF001
                        source_data, AirOS6.derived_wireless_data
                    )
                    new_data = AirOS6Data.from_dict(derived_data)
                else:
                    derived_data = AirOS8._derived_data_helper(  # noqa: SLF001
                        source_data, AirOS8.derived_wireless_data
                    )
                    new_data = AirOS8Data.from_dict(derived_data)

                with open(new_fixture_path, "w", encoding="utf-8") as new:  # noqa: PTH123
                    json.dump(new_data.to_dict(), new, indent=2, sort_keys=True)

                _LOGGER.info("Successfully created '%s'", new_filename)

            except json.JSONDecodeError:
                _LOGGER.error("Skipping '%s': Not a valid JSON file.", filename)
                raise
            except Exception as e:
                _LOGGER.error("Error processing '%s': %s", filename, e)
                raise


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )
    generate_airos_fixtures()
