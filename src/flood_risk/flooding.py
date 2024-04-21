"""Module for looking up flooding risk using GPS coordinates."""

import logging
from pathlib import Path

import pandas as pd
import xarray as xr


class RiskLookup:
    """Class for looking up flooding risk using GPS coordinates.

    Parameters
    ----------
    data_path : str
        Path to the flooding risk TIF files.
    """

    def __init__(self, data_path) -> None:
        self._log = logging.getLogger(self.__class__.__name__)
        self._path = data_path

    def _find_risk_files(self, risk_data: str) -> list:
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
        self._log.info("Searching TIF files in: %s", risk_data)
        files = list(Path(risk_data).glob("*.tif"))
        if not files:
            self._log.error("No TIF files found in: %s", risk_data)
            return []

        self._log.info("Found %d risk files", len(files))
        return files

    def lookup(self, data: pd.DataFrame) -> pd.DataFrame:
        """Look up flooding risk for a DataFrame with Amersfoort coordinates.

        Parameters
        ----------
        data : pandas.DataFrame
            DataFrame with Amersfoort coordinates, must have columns:

            - amersfoort_x
            - amersfoort_y

        Returns
        -------
        pandas.DataFrame
            The coordinate DataFrame with add flooding risk data.
        """
        required = ["amersfoort_x", "amersfoort_y"]
        missing = set(required) - set(data.columns)
        if missing:
            self._log.error("Missing coordinate columns: %s", ", ".join(missing))

        # Create Series of tuples for coordinates.
        coordinates = data.apply(
            lambda row: (row["amersfoort_x"], row["amersfoort_y"]), axis=1
        )

        # Assign risk scores.
        assignments = {}
        risk_files = self._find_risk_files(self._path)
        for risk_file in risk_files:
            risk_file = Path(risk_file)
            column_name = risk_file.name[:-4].lower().replace(" ", "_")

            risk_scores = self._lookup_risks(coordinates, risk_file)
            if risk_scores is not None:
                assignments[column_name] = risk_scores

        return data.assign(**assignments)

    def _lookup_risks(self, coordinates: pd.Series, risk_file: Path) -> pd.Series:
        """Look up risks for a Series of Amersfoort coordinates.

        Parameters
        ----------
        coordinates : pd.Series
            Series of Amersfoort coordinate tuples.
        risk_file : pathlib.Path
            Path to the TIF risk data file.

        Returns
        -------
        pd.Series
            Series of risk scores for the provided GPS coordinates.
        """
        self._log.info("Reading risk data from: %s", risk_file)
        try:
            risk_data = xr.open_dataset(risk_file, engine="rasterio")

        # pylint: disable=broad-exception-caught.
        except Exception as error:
            self._log.warning("Error reading risk data: %s", error)
            return None

        return coordinates.map(
            lambda coords: risk_data.sel(
                x=coords[0], y=coords[1], method="nearest"
            ).band_data.values[0]
        )
