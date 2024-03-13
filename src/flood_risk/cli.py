"""Command Line Interface for looking up risk data."""

import argparse
import logging
import sys
import time
from pathlib import Path
from typing import Union

import pandas as pd
import pyproj
import xarray as xr
from geopy.geocoders import Nominatim

# Initialize logging.
logging.basicConfig(
    format="%(asctime)s - %(levelname)-8s - %(name)-20s %(message)-.150s",
    datefmt="%d-%m-%YT%H:%M:%S",
)
logger = logging.getLogger("FloodingRisk")

# Set up the Nominatim Geocoder service
locator = Nominatim(user_agent="TestGeocoder")


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser("CLI for looking up risk data")
    parser.add_argument(
        "adress_file", type=str, help="CSV file with adresses to look up."
    )
    parser.add_argument("risk_data", type=str, help="Folder with risk data TIFF files")
    parser.add_argument(
        "-o",
        "--output",
        dest="output_file",
        type=str,
        help="CSV file to write results to",
        required=False,
        default="flooding_risks.csv",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        type=str,
        choices=["critical", "error", "warning", "info", "debug"],
        default="info",
        help="Logging level for the terminal, defaults to info.",
    )
    return parser.parse_args()


def find_risk_files(risk_data: str) -> list:
    """Find TIFF risk files in the specfied folder."""
    logger.info("Searching risk files in: %s", risk_data)
    files = list(Path(risk_data).glob("*.tif"))
    if not files:
        logger.error("No risk data TIF files found in: %s", risk_data)
        sys.exit(1)

    logger.info("Found %d risk files", len(files))
    return files


def load_addresses(adress_file: str) -> pd.DataFrame:
    """Loads addresses from CSV."""
    logger.info("Reading addresses from: %s", adress_file)

    try:
        addresses = pd.read_csv(adress_file)

    except FileNotFoundError:
        logger.error("Cannot find address CSV file: %s", adress_file)
        sys.exit(1)

    # pylint: disable=broad-exception-caught
    except Exception as error:
        logger.error("Error reading address CSV file: %s", error)
        sys.exit(1)

    required = {"street", "house_number", "postal_code"}
    missing = required - set(addresses.columns)
    if missing:
        logger.error("Missing columns in the address data: %s", ", ".join(missing))
        sys.exit(1)

    logger.info("Found %d addresses", len(addresses))
    return addresses


def lookup_address(address_row: pd.Series) -> Union[None, tuple]:
    """Look up GPS coordinates for an address."""
    logger.debug(
        "Looking up addres: {street}, {house_number}, {postal_code}", **address_row
    )
    result = locator.geocode(
        {
            "street": f"{address_row['street']} {address_row['house_number']}",
            "postalcode": address_row["postal_code"],
            "country": "The Netherlands",
        }
    )
    # Need to wait at least one second.
    time.sleep(1)

    if not result:
        logger.warning(
            "No GPS coordinates found for: {street}, {house_number}, {postal_code}",
            **address_row,
        )
        return None

    # Re-project GPS coordinates.
    transformer = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:28992")
    return transformer.transform(result.latitude, result.longitude)


def lookup_risks(gps_coords: pd.Series, risk_file: Path) -> pd.Series:
    """Look up risks for a Series of GPS coordinates."""
    logger.info("Looking up risk data from: %s", risk_file)
    try:
        risk_data = xr.open_dataset(risk_file, engine="rasterio")

    # pylint: disable=broad-exception-caught.
    except Exception as error:
        logger.warning("Error reading risk data: %s", error)
        return None

    return gps_coords.map(
        lambda gps_coords: risk_data.sel(
            x=gps_coords[0], y=gps_coords[1], method="nearest"
        ).band_data.values[0]
    )


def main() -> None:
    """Main program routine."""
    args = parse_args()

    # Set logging level to requested level.
    logger.setLevel(args.verbose.upper())
    logger.info("Starting risk lookup process.")

    # Load addresses and find risk files.
    addresses = load_addresses(args.adress_file)
    risk_files = find_risk_files(args.risk_data)

    # Add GPS coordinates.
    addresses = addresses.assign(gps_coords=lambda df: df.apply(lookup_address, axis=1))

    # Add risk indicators.
    for risk_file in risk_files:
        risk_file = Path(risk_file)

        column_name = risk_file.name[:-4].lower().replace(" ", "_")
        risk_scores = lookup_risks(addresses["gps_coords"], risk_file)
        if risk_scores is not None:
            addresses = addresses.assign(**{column_name: risk_scores})

    # Store output
    logger.info("Writing risk output to: %s", args.output_file)
    addresses.to_csv(args.output_file, index=False)

    logger.info("Finished looking up risk!")


if __name__ == "__main__":
    main()
