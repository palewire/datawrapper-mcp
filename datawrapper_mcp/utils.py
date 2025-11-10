"""Utility functions for the Datawrapper MCP server."""

import json
import os

import pandas as pd


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
    if isinstance(data, str):
        # Check if it's a file path that exists
        if os.path.isfile(data):
            if data.endswith(".csv"):
                return pd.read_csv(data)
            elif data.endswith(".json"):
                with open(data) as f:
                    file_data = json.load(f)
                # Recursively process the loaded JSON data
                return json_to_dataframe(file_data)
            else:
                raise ValueError(
                    f"Unsupported file type: {data}\n\n"
                    "Supported file types:\n"
                    "  - .csv (CSV files)\n"
                    "  - .json (JSON files containing list of dicts or dict of arrays)"
                )

        # Check if it looks like CSV content (not a file path)
        if "\n" in data and "," in data and not data.strip().startswith(("[", "{")):
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
            data = json.loads(data)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Invalid JSON string: {e}\n\n"
                "Expected one of:\n"
                "  1. File path: '/path/to/data.csv' or '/path/to/data.json'\n"
                '  2. JSON string: \'[{"year": 2020, "value": 100}, ...]\'\n'
                '  3. JSON string: \'{"year": [2020, 2021], "value": [100, 150]}\''
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
            value_types = [type(v).__name__ for v in data.values()]
            raise ValueError(
                "Dict format must have lists as values.\n\n"
                "Expected format:\n"
                '  {"year": [2020, 2021], "value": [100, 150]}\n\n'
                f"Got dict with values of type: {value_types}"
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
