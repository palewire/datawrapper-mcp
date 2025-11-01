"""Utility functions for the Datawrapper MCP server."""

import json
import os

import pandas as pd


def get_api_token() -> str:
    """Get the Datawrapper API token from environment."""
    api_token = os.environ.get("DATAWRAPPER_API_TOKEN")
    if not api_token:
        raise ValueError(
            "DATAWRAPPER_API_TOKEN environment variable is required. "
            "Get your token from https://app.datawrapper.de/account/api-tokens"
        )
    return api_token


def json_to_dataframe(data: str | list | dict) -> pd.DataFrame:
    """Convert JSON data to a pandas DataFrame.

    Args:
        data: One of:
            - List of records: [{"col1": val1, "col2": val2}, ...]
            - Dict of arrays: {"col1": [val1, val2], "col2": [val3, val4]}
            - JSON string in either format above

    Returns:
        pandas DataFrame

    Examples:
        >>> json_to_dataframe([{"a": 1, "b": 2}, {"a": 3, "b": 4}])
        >>> json_to_dataframe({"a": [1, 3], "b": [2, 4]})
        >>> json_to_dataframe('[{"a": 1, "b": 2}]')
    """
    if isinstance(data, str):
        # Check if it looks like a file path
        if data.endswith((".csv", ".json", ".txt")) or "/" in data or "\\" in data:
            raise ValueError(
                "File paths are not supported. Please read the file first and pass the data.\n\n"
                "For CSV files:\n"
                "  1. Read the file into a list of dicts or dict of arrays\n"
                "  2. Pass that data structure to this tool\n\n"
                "Example:\n"
                '  data = [{"year": 2020, "value": 100}, {"year": 2021, "value": 150}]'
            )

        # Check if it looks like CSV content
        if "\n" in data and "," in data and not data.strip().startswith(("[", "{")):
            raise ValueError(
                "CSV strings are not supported. Please parse the CSV first.\n\n"
                "Convert CSV to one of these formats:\n"
                '  1. List of dicts: [{"col": val}, ...]\n'
                '  2. Dict of arrays: {"col": [vals]}\n\n'
                "Example:\n"
                '  data = [{"year": 2020, "value": 100}, {"year": 2021, "value": 150}]'
            )

        try:
            data = json.loads(data)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Invalid JSON string: {e}\n\n"
                "Expected JSON in one of these formats:\n"
                '  1. \'[{"year": 2020, "value": 100}, {"year": 2021, "value": 150}]\'\n'
                '  2. \'{"year": [2020, 2021], "value": [100, 150]}\''
            )

    if isinstance(data, list):
        if not data:
            raise ValueError(
                "Data list is empty. Please provide at least one row of data."
            )
        if not all(isinstance(item, dict) for item in data):
            raise ValueError(
                "List format must contain dictionaries.\n\n"
                "Expected format:\n"
                '  [{"year": 2020, "value": 100}, {"year": 2021, "value": 150}]\n\n'
                f"Got: {type(data[0]).__name__} in list"
            )
        # List of records: [{"col1": val1, "col2": val2}, ...]
        return pd.DataFrame(data)
    elif isinstance(data, dict):
        if not data:
            raise ValueError(
                "Data dict is empty. Please provide at least one column of data."
            )
        # Check if it's a dict of arrays (all values should be lists)
        if not all(isinstance(v, list) for v in data.values()):
            raise ValueError(
                "Dict format must have lists as values.\n\n"
                "Expected format:\n"
                '  {"year": [2020, 2021], "value": [100, 150]}\n\n'
                f"Got dict with values of type: {[type(v).__name__ for v in data.values()]}"
            )
        # Dict of arrays: {"col1": [val1, val2], "col2": [val3, val4]}
        return pd.DataFrame(data)
    else:
        raise ValueError(
            f"Unsupported data type: {type(data).__name__}\n\n"
            "Data must be one of:\n"
            '  1. List of dicts: [{"year": 2020, "value": 100}, ...]\n'
            '  2. Dict of arrays: {"year": [2020, 2021], "value": [100, 150]}\n'
            "  3. JSON string in either format above"
        )
