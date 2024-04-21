"""Command Line Interface for looking up risk data."""

import argparse
import logging
import sys

import pandas as pd
from flood_risk.bag import BAGLookup
from flood_risk.flooding import RiskLookup
from flood_risk.nominatim import NominatimLookup

# Initialize logging.
logging.basicConfig(
    format="%(asctime)s - %(levelname)-8s - %(name)-20s %(message)-.150s",
    datefmt="%d-%m-%YT%H:%M:%S",
)
logger = logging.getLogger("FloodingRisk")


def parse_args() -> argparse.Namespace:
    """Parse command line arguments.

    Returns
    -------
    argparse.Namespace
        Command line arguments as Namespace object.
    """
    parser = argparse.ArgumentParser("CLI for looking up risk data")
    parser.add_argument(
        "address_file",
        type=str,
        help="CSV file with addresses to look up.",
    )
    parser.add_argument(
        "-r",
        "--risk",
        dest="risk_path",
        type=str,
        help="Folder containing flooding risk TIFF files",
        default="risk_data/",
        required=False,
    )
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
        "-m",
        "--method",
        dest="method",
        type=str,
        help="Method for looking up geographical locations",
        choices=["bag", "nominatim"],
        default="nominatim",
        required=False,
    )
    parser.add_argument(
        "-b",
        "--bag",
        dest="bag_path",
        type=str,
        help="Path to the BAG data file.",
        default="bag_data/bag-light.gpkg",
        required=False,
    )
    parser.add_argument(
        "-v",
        "--verbose",
        type=str,
        help="Logging level for the terminal, defaults to info.",
        choices=["critical", "error", "warning", "info", "debug"],
        default="info",
    )
    return parser.parse_args()


def load_addresses(address_file: str) -> pd.DataFrame:
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
    logger.info("Reading addresses from: %s", address_file)

    try:
        addresses = pd.read_csv(address_file)

    except FileNotFoundError:
        logger.error("Cannot find address CSV file: %s", address_file)
        sys.exit(1)

    # pylint: disable=broad-exception-caught
    except Exception as error:
        logger.error("Error reading address CSV file: %s", error)
        sys.exit(1)

    logger.info("Found %d addresses", len(addresses))
    return addresses


def main() -> None:
    """Main program routine."""
    args = parse_args()

    # Set logging level to requested level.
    logger.setLevel(args.verbose.upper())
    logger.info("Starting flooding risk lookup.")

    # Load addresses and find risk files.
    addresses = load_addresses(args.address_file)

    # Look up geoghraphical locations for addresses.
    if args.method == "bag":
        try:
            bag = BAGLookup(args.bag_path)
            locations = bag.lookup(addresses)
        except RuntimeError as error:
            logger.error("Error looking op geographical locations: %s.", error)
            sys.exit(1)

    else:
        nominatim = NominatimLookup()
        locations = nominatim.lookup(addresses)

    # Add risk indicators.
    risk = RiskLookup(args.risk_path)
    risk_data = risk.lookup(locations)

    # Store output
    logger.info("Writing flooding risk output to: %s", args.output_file)
    risk_data.to_csv(args.output_file, index=False)

    logger.info("Finished looking up flooding risks!")


if __name__ == "__main__":
    main()
