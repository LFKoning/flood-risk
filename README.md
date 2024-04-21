
# Flooding Risks

## Goal

This package provides a tool to determine flooding risks for Dutch addresses. The flooding risks are based on the [Klimaateffectatlas](https://www.klimaateffectatlas.nl/nl/).

To use this tool, you will first need to download the Klimaateffectatlas data from: [https://www.klimaateffectatlas.nl/nl/data-opvragen](https://www.klimaateffectatlas.nl/nl/data-opvragen). In this data you will find the spatial TIF files required by the tool.

## Installation

### For regular users

If you just want to use this project, you can simply install it with:

```shell
python -m pip install git+https://github.com/LFKoning/flood-risk.git
```

This will install the package and all of its dependencies into your current Python environment.

### For developers

If you want to help develop this project, please follow the following steps to get started.


Clone the repository from Github to hard drive:

```shell
git clone https://github.com/LFKoning/flood-risk.git
```

Then install the package and its development dependencies using pip:

```shell
python -m pip install -e flood-risk[dev]
```

## Usage

This tool offers a Command Line Interface (CLI), for more info type:

```shell
floodrisk -h
```

To use the tool with default settings, type:

```shell
floodrisk my_addresses.csv

```

This will process all addresses found in `my_addresses.csv`. The tool will first look up
the geographical locations for all addresses using Nominatim. Then it will add flooding
risks using TIF files found in the `risk_data/` folder. Finally, it stores the output in
 `flooding_risks.csv`.

You can change all settings using the command line:

| argument    | short | description                                           | default                   |
| ----------- | ----- | ----------------------------------------------------- | ------------------------- |
| `--risk`    | `-r`  | Path to the folder containing TIF files.              | `./risk_data/`            |
| `--output`  | `-o`  | Path for the output CSV file.                         | `./flooding_risk.csv`     |
| `--method`  | `-m`  | Method for address geolocation; `bag` of `nominatim`. | `nominatim`               |
| `--bag`     | `-b`  | Path to the BAG geopackage file.                      | `bag_data/bag-light.gpkg` |
| `--verbose` | `-v`  | Logging verbosity level for the terminal.             | `info`                    |

To use the `bag` method for geolocating addresses, please download the data from:

- Website: https://service.pdok.nl/lv/bag/atom/bag.xml
- Direct download: https://service.pdok.nl/lv/bag/atom/downloads/bag-light.gpkg


## Address CSV Format

The first argument for the tool should be a CSV file with the addresses which should
contain these columns:

| column         | description                   | example        |
| -------------- | ----------------------------- | -------------- |
| `street`       | Street name for the address.  | `Bakkerstraat` |
| `house_number` | House number, numerical part. | `3`            |
| `house_letter` | House number, letter part.    | `A`            |
| `house_suffix` | House nummber suffix.         | `III`          |
| `postcode`     | Dutch 6-character postal code | `1234 AB`      |

*Note: Any additional columns will be left as-is and will also appear in the output.*

## Risk data TIF files

The `risk` argument should point to a folder containing the TIF data files from the
[Klimaateffectatlas]([https://](https://www.klimaateffectatlas.nl/nl/)). Note that the
tool will process **all** TIF files it finds in the specified folder!

## Contributing

If you want to contribute to this project, feel free to clone the code, make
improvements and open a pull request!

If you have suggestions or remarks not directly related to the project's code or
documentation, feel free to e-mail the authors.

## Maintainers

This project is maintained by:

1. [lukas.koning@afm.nl](lukas.koning@afm.nl)

