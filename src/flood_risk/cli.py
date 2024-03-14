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
    """Parse command line arguments.

    Returns
    -------
    argparse.Namespace
        Command line arguments as Namespace object.
    """
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
    """Find TIFF risk files in the specfied folder.

    Parameters
    ----------
    risk_data : str
        Folder containing TIF risk data files.

    Returns
    -------
    list
        List of Path objects for each TIF file found.
    """
    logger.info("Searching risk files in: %s", risk_data)
    files = list(Path(risk_data).glob("*.tif"))
    if not files:
        logger.error("No risk data TIF files found in: %s", risk_data)
        sys.exit(1)

    logger.info("Found %d risk files", len(files))
    return files


def load_addresses(adress_file: str) -> pd.DataFrame:
    """Loads addresses from CSV.

    Parameters
    ----------
    address_file : str
        Path to the CSV file with addresses to look up.

    Returns
    -------
    pandas.DataFrame
        DataFrame with address data.
    """
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


def lookup_address(
    street: str, house_number: str, postal_code: str
) -> Union[dict, None]:
    """Look up GPS coordinates for an address.

    Parameters
    ----------
    street : str
        Street name for the address, excluding house number.
    house_number : str
        House number including any suffixes.
    postal_code : str
        Dutch 6-character postal code.

    Returns
    -------
    dict or None
        Dict with location information from the Geocoder or
        None if the address was not found.

    """
    logger.debug(
        f"Looking up addres: {street}, {house_number}, {postal_code}",
    )
    location = locator.geocode(
        {
            "street": f"{street} {house_number}",
            "postalcode": postal_code,
            "country": "The Netherlands",
        },
        exactly_one=True,
        addressdetails=True,
    )

    # Need to wait at least one second.
    time.sleep(1)

    if not location:
        logger.warning(
            f"No location found for: {street}, {house_number}, {postal_code}"
        )
        return None

    # Return result.
    geo_data = {"geocode_coordinates": (location.latitude, location.longitude)}
    for field in "road", "house_number", "village", "municipality", "state", "postcode":
        geo_data[f"geocode_{field}"] = location.raw["address"].get(field)

    return geo_data


def lookup_risks(gps_coordinates: pd.Series, risk_file: Path) -> pd.Series:
    """Look up risks for a Series of GPS coordinates.

    Parameters
    ----------
    gps_cooridnates : pd.Series
        Series object with latitiude, longitude tuples.
    risk_file : pathlib.Path
        Path to the TIF risk data file.

    Returns
    -------
    pd.Series
        Series of risk scores for the provided GPS coordinates.
    """
    logger.info("Reading risk data from: %s", risk_file)
    try:
        risk_data = xr.open_dataset(risk_file, engine="rasterio")

    # pylint: disable=broad-exception-caught.
    except Exception as error:
        logger.warning("Error reading risk data: %s", error)
        return None

    # Transform coordinates to target projection.
    target_projection = risk_data.rio.crs.to_string()
    logger.debug("Tranforming coordinates to projection: %s", target_projection)
    transformer = pyproj.Transformer.from_crs("EPSG:4326", target_projection)
    transformed_coordinates = pd.Series(transformer.itransform(gps_coordinates))

    return transformed_coordinates.map(
        lambda coords: risk_data.sel(
            x=coords[0], y=coords[1], method="nearest"
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

    # Add Geocoder location details.
    locations = addresses.apply(
        lambda row: lookup_address(
            row["street"], row["house_number"], row["postal_code"]
        ),
        axis=1,
    )
    locations = pd.json_normalize(locations)
    addresses = addresses.join(locations)

    # Add risk indicators.
    for risk_file in risk_files:
        risk_file = Path(risk_file)

        column_name = risk_file.name[:-4].lower().replace(" ", "_")
        risk_scores = lookup_risks(addresses["geocode_coordinates"], risk_file)
        if risk_scores is not None:
            addresses = addresses.assign(**{column_name: risk_scores})

    # Store output
    logger.info("Writing risk output to: %s", args.output_file)
    addresses.to_csv(args.output_file, index=False)

    logger.info("Finished looking up risk!")


if __name__ == "__main__":
    main()
