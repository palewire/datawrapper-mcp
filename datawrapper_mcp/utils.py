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
        try:
            data = json.loads(data)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON string: {e}")

    if isinstance(data, list):
        # List of records: [{"col1": val1, "col2": val2}, ...]
        return pd.DataFrame(data)
    elif isinstance(data, dict):
        # Dict of arrays: {"col1": [val1, val2], "col2": [val3, val4]}
        return pd.DataFrame(data)
    else:
        raise ValueError(
            "Data must be one of:\n"
            '  - List of dicts: [{"col": val}, ...]\n'
            '  - Dict of arrays: {"col": [vals]}\n'
            "  - JSON string in either format"
        )
