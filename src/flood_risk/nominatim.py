"""Module for looking up GPS coordinates for addresses using Nominatim."""

import logging
import re
import time
from typing import Union

import pandas as pd
from geopy.geocoders import Nominatim
from pyproj import Transformer


class NominatimLookup:
    """Class for looking up addresses using Nominatim."""

    def __init__(self) -> None:
        self._log = logging.getLogger(self.__class__.__name__)
        self._locator = Nominatim(user_agent="TestGeocoder")
        self._transformer = Transformer.from_crs("EPSG:4326", "EPSG:28992")

    def lookup(self, addresses: pd.DataFrame) -> pd.DataFrame:
        """Look up GPS coordinates for a DataFrame with addresses.

        Parameters
        ----------
        addresses : pandas.DataFrame
            DataFrame with addresses, should have these columns:

            - street
            - postcode
            - house_number
            - house_letter
            - house_suffix

        Returns
        -------
        pandas.DataFrame
            Addresses DataFrame including GPS-coordinates.
        """
        required = [
            "street",
            "postcode",
            "house_number",
            "house_letter",
            "house_suffix",
        ]
        missing = set(required) - set(addresses.columns)
        if missing:
            self._log.error("Missing address columns: %s", ", ".join(missing))

        # Format postcodes as 4 digits <space> 2 letters.
        addresses = addresses.assign(
            postcode=lambda df: df["postcode"].map(self._format_pc6),
        )

        coordinates = addresses.apply(self._lookup_address, axis=1)
        return addresses.join(pd.json_normalize(coordinates))

    def _lookup_address(self, address: pd.Series) -> Union[dict, None]:
        """Look up GPS coordinates for an address.

        Parameters
        ----------
        address : pd.Series
            Address row including street, postcode and house number.

        Returns
        -------
        dict or None
            Dict containing GPS and Amersfoort coordinates.
            None is returned if no location was found.
        """
        street = self._format_street(address)
        self._log.debug("Looking up address: %s, %s", street, address["postcode"])
        location = self._locator.geocode(
            {
                "street": street,
                "postalcode": address["postcode"],
                "country": "Nederland",
            },
            exactly_one=True,
        )

        # Need to wait at least one second.
        time.sleep(1)

        if not location:
            self._log.warning(
                "No location found for: %s, %s", street, address["postcode"]
            )
            return None

        # Get Amersfoort coordinates.
        # pylint: disable=unpacking-non-sequence
        x, y = self._transformer.transform(location.latitude, location.longitude)

        return {
            "longitude": location.longitude,
            "latitude": location.latitude,
            "amersfoort_x": x,
            "amersfoort_y": y,
        }

    @staticmethod
    def _format_street(address: pd.Series) -> str:
        """Format street and house number wit optional components."""
        output = f"{address['street']} {address['house_number']}"
        if pd.notna(address["house_letter"]):
            output += str(address["house_letter"])
        if pd.notna(address["house_suffix"]):
            output += " " + str(address["house_suffix"])

        return output

    @staticmethod
    def _format_pc6(postcode: str) -> str:
        """Format postcode as 4 digits <space> 2 letters."""
        return re.sub(r"(\d{4})\s*(\w{2})", r"\1 \2", postcode)
