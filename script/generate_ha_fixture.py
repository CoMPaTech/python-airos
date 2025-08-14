"""Generate mock airos fixtures for testing."""

import json
import logging
import os
import sys

_LOGGER = logging.getLogger(__name__)

current_script_dir = os.path.dirname(os.path.abspath(__file__))
project_root_dir = os.path.abspath(os.path.join(current_script_dir, os.pardir))

if project_root_dir not in sys.path:
    sys.path.append(project_root_dir)

# NOTE: This assumes the airos module is correctly installed or available in the project path.
# If not, you might need to adjust the import statement.
from airos.airos8 import AirOS  # noqa: E402
from airos.data import AirOS8Data as AirOSData  # noqa: E402


def generate_airos_fixtures() -> None:
    """Process all (intended) JSON files from the userdata directory to potential fixtures."""

    # Define the paths to the directories
    fixture_dir = os.path.join(os.path.dirname(__file__), "../fixtures")
    userdata_dir = os.path.join(os.path.dirname(__file__), "../fixtures/userdata")

    # Ensure the fixture directory exists
    os.makedirs(fixture_dir, exist_ok=True)

    # Iterate over all files in the userdata_dir
    for filename in os.listdir(userdata_dir):
        if "mocked" in filename:
            continue
        if filename.endswith(".json"):
            # Construct the full paths for the base and new fixtures
            base_fixture_path = os.path.join(userdata_dir, filename)
            new_filename = f"airos_{filename}"
            new_fixture_path = os.path.join(fixture_dir, new_filename)

            _LOGGER.info("Processing '%s'...", filename)

            try:
                with open(base_fixture_path, encoding="utf-8") as source:
                    source_data = json.loads(source.read())

                derived_data = AirOS.derived_data(source_data)
                new_data = AirOSData.from_dict(derived_data)

                with open(new_fixture_path, "w", encoding="utf-8") as new:
                    json.dump(new_data.to_dict(), new, indent=2, sort_keys=True)

                _LOGGER.info("Successfully created '%s'", new_filename)

            except json.JSONDecodeError:
                _LOGGER.error("Skipping '%s': Not a valid JSON file.", filename)
            except Exception as e:
                _LOGGER.error("Error processing '%s': %s", filename, e)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )
    generate_airos_fixtures()
