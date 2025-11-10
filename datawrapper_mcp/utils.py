"""Utility functions for the Datawrapper MCP server."""

import json
import os

import pandas as pd

from .logging import get_logger

logger = get_logger("utils")


def get_api_token() -> str:
    """Get the Datawrapper API token from environment."""
    logger.debug("Retrieving API token from environment")
    api_token = os.environ.get("DATAWRAPPER_ACCESS_TOKEN")
    if not api_token:
        logger.error("API token not found in environment")
        raise ValueError(
            "DATAWRAPPER_ACCESS_TOKEN environment variable is required. "
            "Get your token from https://app.datawrapper.de/account/api-tokens"
        )
    logger.debug("API token retrieved successfully")
    # SECURITY: Never log the actual token value
    return api_token


def json_to_dataframe(data: str | list | dict) -> pd.DataFrame:
    """Convert JSON data to a pandas DataFrame.

    Args:
        data: One of:
            - File path to CSV or JSON file (e.g., "/path/to/data.csv")
            - List of records: [{"col1": val1, "col2": val2}, ...]
            - Dict of arrays: {"col1": [val1, val2], "col2": [val3, val4]}
            - JSON string in either format above

    Returns:
        pandas DataFrame

    Examples:
        >>> json_to_dataframe("/tmp/data.csv")
        >>> json_to_dataframe("/tmp/data.json")
        >>> json_to_dataframe([{"a": 1, "b": 2}, {"a": 3, "b": 4}])
        >>> json_to_dataframe({"a": [1, 3], "b": [2, 4]})
        >>> json_to_dataframe('[{"a": 1, "b": 2}]')
    """
    data_type = type(data).__name__
    logger.debug("Converting data to DataFrame", extra={"data_type": data_type})

    if isinstance(data, str):
        # Check if it's a file path that exists
        if os.path.isfile(data):
            logger.debug("Reading data from file", extra={"file_path": data})
            if data.endswith(".csv"):
                df = pd.read_csv(data)
                logger.debug(
                    "CSV file loaded successfully",
                    extra={"rows": len(df), "columns": len(df.columns)},
                )
                return df
            elif data.endswith(".json"):
                with open(data) as f:
                    file_data = json.load(f)
                # Recursively process the loaded JSON data
                return json_to_dataframe(file_data)
            else:
                logger.error("Unsupported file type", extra={"file_path": data})
                raise ValueError(
                    f"Unsupported file type: {data}\n\n"
                    "Supported file types:\n"
                    "  - .csv (CSV files)\n"
                    "  - .json (JSON files containing list of dicts or dict of arrays)"
                )

        # Check if it looks like CSV content (not a file path)
        if "\n" in data and "," in data and not data.strip().startswith(("[", "{")):
            logger.error("CSV string detected (not supported)")
            raise ValueError(
                "CSV strings are not supported. Please save to a file first.\n\n"
                "Options:\n"
                "  1. Save CSV to a file and pass the file path\n"
                '  2. Parse CSV to list of dicts: [{"col": val}, ...]\n'
                '  3. Parse CSV to dict of arrays: {"col": [vals]}\n\n'
                "Example:\n"
                '  data = [{"year": 2020, "value": 100}, {"year": 2021, "value": 150}]'
            )

        # Try to parse as JSON string
        try:
            logger.debug("Parsing JSON string")
            data = json.loads(data)
            logger.debug("JSON string parsed successfully")
        except json.JSONDecodeError as e:
            logger.error("Invalid JSON string", extra={"error": str(e)})
            raise ValueError(
                f"Invalid JSON string: {e}\n\n"
                "Expected one of:\n"
                "  1. File path: '/path/to/data.csv' or '/path/to/data.json'\n"
                '  2. JSON string: \'[{"year": 2020, "value": 100}, ...]\'\n'
                '  3. JSON string: \'{"year": [2020, 2021], "value": [100, 150]}\''
            )

    if isinstance(data, list):
        if not data:
            logger.error("Empty data list provided")
            raise ValueError(
                "Data list is empty. Please provide at least one row of data."
            )
        if not all(isinstance(item, dict) for item in data):
            logger.error(
                "Invalid list format", extra={"item_type": type(data[0]).__name__}
            )
            raise ValueError(
                "List format must contain dictionaries.\n\n"
                "Expected format:\n"
                '  [{"year": 2020, "value": 100}, {"year": 2021, "value": 150}]\n\n'
                f"Got: {type(data[0]).__name__} in list"
            )
        # List of records: [{"col1": val1, "col2": val2}, ...]
        df = pd.DataFrame(data)
        logger.debug(
            "DataFrame created from list of records",
            extra={"rows": len(df), "columns": len(df.columns)},
        )
        return df
    elif isinstance(data, dict):
        if not data:
            logger.error("Empty data dict provided")
            raise ValueError(
                "Data dict is empty. Please provide at least one column of data."
            )
        # Check if it's a dict of arrays (all values should be lists)
        if not all(isinstance(v, list) for v in data.values()):
            value_types = [type(v).__name__ for v in data.values()]
            logger.error("Invalid dict format", extra={"value_types": value_types})
            raise ValueError(
                "Dict format must have lists as values.\n\n"
                "Expected format:\n"
                '  {"year": [2020, 2021], "value": [100, 150]}\n\n'
                f"Got dict with values of type: {value_types}"
            )
        # Dict of arrays: {"col1": [val1, val2], "col2": [val3, val4]}
        df = pd.DataFrame(data)
        logger.debug(
            "DataFrame created from dict of arrays",
            extra={"rows": len(df), "columns": len(df.columns)},
        )
        return df
    else:
        logger.error("Unsupported data type", extra={"data_type": type(data).__name__})
        raise ValueError(
            f"Unsupported data type: {type(data).__name__}\n\n"
            "Data must be one of:\n"
            '  1. List of dicts: [{"year": 2020, "value": 100}, ...]\n'
            '  2. Dict of arrays: {"year": [2020, 2021], "value": [100, 150]}\n'
            "  3. JSON string in either format above"
        )
