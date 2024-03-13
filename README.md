
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

To use the tool, type:

```shell
floodrisk <CSV file with addresses> <flood risk data>
```

The first argument should be a CSV file with the addresses to look up, and it should contain these columns:

|column|description|example|
|---|---|--|
|`street`|Street name for the address|`Bakkerstraat`|
|`house_number`|House number including suffixes|`3a`|
|`postal_code`|Dutch 6-character postal code|`1234 AB`|

*Note: Any additional columns will be left as-is and will also appear in the output.*

The second argument should point to the folder containing the TIF data files from the Klimaateffectatlas. Note that the tool will process any TIF file it finds, so only include the TIF files you are interested in!

## Contributing

If you want to contribute to this project, feel free to clone the code, make
improvements and open a pull request!

If you have suggestions or remarks not directly related to the project's code or
documentation, feel free to e-mail the authors.

## Maintainers

This project is maintained by:

1. [lukas.koning@afm.nl](lukas.koning@afm.nl)

