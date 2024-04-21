"""Module for looking up GPS coordinates for addresses using BAG data."""

import logging
import os
import re
import sqlite3
from typing import Any, Union

import pandas as pd
from pyproj import Transformer


class BAGLookup:
    """Class for looking up addresses in BAG data.

    Parameters
    ----------
    bag_path : str
        Path to the BAG geopackage file.
    """

    def __init__(self, bag_path: str) -> None:
        self._log = logging.getLogger(self.__class__.__name__)
        self._transformer = Transformer.from_crs("EPSG:28992", "EPSG:4326")
        self._database = self._connect(bag_path)

    def lookup(self, addresses: pd.DataFrame) -> pd.DataFrame:
        """Look up GPS coordinates for a DataFrame with addresses.

        Parameters
        ----------
        addresses : pandas.DataFrame
            DataFrame with addresses, should have these columns:

            - postcode
            - house_number
            - house_letter
            - house_suffix

        Returns
        -------
        pandas.DataFrame
            Addresses DataFrame including GPS-coordinates.
        """
        required = ["postcode", "house_number", "house_letter", "house_suffix"]
        missing = set(required) - set(addresses.columns)
        if missing:
            self._log.error("Missing address columns: %s", ", ".join(missing))

        # Format postcode and uppercase address components.
        addresses = addresses.assign(
            postcode=lambda df: df["postcode"].map(self._format_pc6),
            house_letter=lambda df: df["house_letter"].map(self._make_upper),
            house_suffix=lambda df: df["house_suffix"].map(self._make_upper),
        )

        coordinates = addresses[required].apply(self._lookup_address, axis=1)
        return addresses.join(pd.json_normalize(coordinates))

    def _connect(self, bag_path):
        """Connect to the BAG data file.

        Parameters
        ----------
        bag_path : str
            Path to the BAG geopackage file.


        Returns
        -------
        sqlite3.Connection
            SQLite3 database connection.
        """
        self._log.debug("Connecting to BAG data: %s", bag_path)
        # Must be an existing database, do not create one.
        if not os.path.isfile(bag_path):
            raise RuntimeError(f"BAG data not found at: {bag_path}")

        try:
            return sqlite3.connect(bag_path)
        except sqlite3.OperationalError as error:
            raise RuntimeError(f"Could not open BAG data from: {bag_path}") from error

    @staticmethod
    def _make_upper(value: Any) -> Any:
        """Uppercase strings leaving other types as-is."""
        return value.upper() if hasattr(value, "upper") else value

    @staticmethod
    def _format_address(address: pd.Series) -> str:
        """Format addresses."""
        output = f"{address['postcode']}, {address['house_number']}"
        if pd.notna(address["house_letter"]):
            output += str(address["house_letter"])
        if pd.notna(address["house_suffix"]):
            output += " " + address["house_suffix"]
        return output

    @staticmethod
    def _format_pc6(postcode: str) -> str:
        """Format postcodes as 4 digits 2 letters without a space."""
        return re.sub(r"(\d{4})\s*(\w{2})", r"\1\2", postcode)

    def _lookup_address(self, address: pd.Series) -> Union[dict, None]:
        """Look up a single address.

        Parameters
        ----------
        address : pd.Series
            Address row including postcode and house number.

        Returns
        -------
        dict or None
            Dict containing GPS and Amersfoort coordinates.
            None is returned if no location was found.
        """
        address_str = self._format_address(address)
        self._log.debug("Looking up address: %s", address_str)

        params = ["postcode", "house_number"]
        query = """
            SELECT
                minx, maxx, miny, maxy
            FROM verblijfsobject vo
            LEFT JOIN rtree_verblijfsobject_geom rvo
                ON vo.feature_id = rvo.id
            WHERE
                postcode = ?
                AND huisnummer = ?
        """
        if pd.notna(address["house_letter"]):
            params.append("house_letter")
            query += " AND UPPER(huisletter) = ?"

        if pd.notna(address["house_suffix"]):
            params.append("house_suffix")
            query += " AND UPPER(toevoeging) = ?"

        try:
            result = self._database.execute(query, list(address[params]))
        except sqlite3.OperationalError as error:
            raise RuntimeError(f"Failed to query BAG data: {error}") from error

        location = result.fetchone()
        if not location:
            self._log.warning("No location found for: %s", address_str)
            return None

        # Add and convert coordinates.
        fields = [field[0] for field in result.description]
        location = dict(zip(fields, location))

        # Compute and convert coordinates.
        loc_x = (location["minx"] + location["maxx"]) / 2
        loc_y = (location["miny"] + location["maxy"]) / 2
        # pylint: disable=unpacking-non-sequence
        gps_lat, gps_lon = self._transformer.transform(loc_x, loc_y)

        return {
            "longitude": gps_lon,
            "latitude": gps_lat,
            "amersfoort_x": loc_x,
            "amersfoort_y": loc_y,
        }
