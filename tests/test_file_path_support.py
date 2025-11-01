"""Tests for file path support in json_to_dataframe."""

import json
import os
import tempfile

import pandas as pd
import pytest

from datawrapper_mcp.utils import json_to_dataframe


class TestFilePathSupport:
    """Test file path support in json_to_dataframe."""

    def test_csv_file_path(self):
        """Test loading data from a CSV file."""
        # Create a temporary CSV file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("year,value\n")
            f.write("2020,100\n")
            f.write("2021,150\n")
            f.write("2022,200\n")
            csv_path = f.name

        try:
            # Load the CSV file
            df = json_to_dataframe(csv_path)

            # Verify the data
            assert len(df) == 3
            assert list(df.columns) == ["year", "value"]
            assert df["year"].tolist() == [2020, 2021, 2022]
            assert df["value"].tolist() == [100, 150, 200]
        finally:
            # Clean up
            os.unlink(csv_path)

    def test_json_file_path_list_of_dicts(self):
        """Test loading data from a JSON file (list of dicts format)."""
        data = [
            {"year": 2020, "value": 100},
            {"year": 2021, "value": 150},
            {"year": 2022, "value": 200},
        ]

        # Create a temporary JSON file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            json_path = f.name

        try:
            # Load the JSON file
            df = json_to_dataframe(json_path)

            # Verify the data
            assert len(df) == 3
            assert list(df.columns) == ["year", "value"]
            assert df["year"].tolist() == [2020, 2021, 2022]
            assert df["value"].tolist() == [100, 150, 200]
        finally:
            # Clean up
            os.unlink(json_path)

    def test_json_file_path_dict_of_arrays(self):
        """Test loading data from a JSON file (dict of arrays format)."""
        data = {"year": [2020, 2021, 2022], "value": [100, 150, 200]}

        # Create a temporary JSON file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            json_path = f.name

        try:
            # Load the JSON file
            df = json_to_dataframe(json_path)

            # Verify the data
            assert len(df) == 3
            assert list(df.columns) == ["year", "value"]
            assert df["year"].tolist() == [2020, 2021, 2022]
            assert df["value"].tolist() == [100, 150, 200]
        finally:
            # Clean up
            os.unlink(json_path)

    def test_large_json_file(self):
        """Test loading a large JSON file (1000+ rows)."""
        # Create a large dataset
        data = [{"id": i, "value": i * 10} for i in range(1006)]

        # Create a temporary JSON file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            json_path = f.name

        try:
            # Load the JSON file
            df = json_to_dataframe(json_path)

            # Verify the data
            assert len(df) == 1006
            assert list(df.columns) == ["id", "value"]
            assert df["id"].iloc[0] == 0
            assert df["id"].iloc[-1] == 1005
            assert df["value"].iloc[0] == 0
            assert df["value"].iloc[-1] == 10050
        finally:
            # Clean up
            os.unlink(json_path)

    def test_json_file_with_null_values(self):
        """Test loading JSON file with null values."""
        data = [
            {"year": 2020, "value": 100},
            {"year": 2021, "value": None},
            {"year": 2022, "value": 200},
        ]

        # Create a temporary JSON file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            json_path = f.name

        try:
            # Load the JSON file
            df = json_to_dataframe(json_path)

            # Verify the data
            assert len(df) == 3
            assert list(df.columns) == ["year", "value"]
            assert df["year"].tolist() == [2020, 2021, 2022]
            assert df["value"].iloc[0] == 100
            assert pd.isna(df["value"].iloc[1])
            assert df["value"].iloc[2] == 200
        finally:
            # Clean up
            os.unlink(json_path)

    def test_unsupported_file_type(self):
        """Test that unsupported file types raise an error."""
        # Create a temporary file with unsupported extension
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("some data")
            txt_path = f.name

        try:
            with pytest.raises(ValueError, match="Unsupported file type"):
                json_to_dataframe(txt_path)
        finally:
            # Clean up
            os.unlink(txt_path)

    def test_nonexistent_file_path(self):
        """Test that nonexistent file paths are treated as JSON strings."""
        # This should fail as invalid JSON, not as a missing file
        with pytest.raises(ValueError, match="Invalid JSON string"):
            json_to_dataframe("/nonexistent/path/to/file.json")

    def test_backward_compatibility_list_of_dicts(self):
        """Test that list of dicts still works (backward compatibility)."""
        data = [
            {"year": 2020, "value": 100},
            {"year": 2021, "value": 150},
        ]

        df = json_to_dataframe(data)

        assert len(df) == 2
        assert list(df.columns) == ["year", "value"]
        assert df["year"].tolist() == [2020, 2021]
        assert df["value"].tolist() == [100, 150]

    def test_backward_compatibility_dict_of_arrays(self):
        """Test that dict of arrays still works (backward compatibility)."""
        data = {"year": [2020, 2021], "value": [100, 150]}

        df = json_to_dataframe(data)

        assert len(df) == 2
        assert list(df.columns) == ["year", "value"]
        assert df["year"].tolist() == [2020, 2021]
        assert df["value"].tolist() == [100, 150]

    def test_backward_compatibility_json_string(self):
        """Test that JSON strings still work (backward compatibility)."""
        data = '[{"year": 2020, "value": 100}, {"year": 2021, "value": 150}]'

        df = json_to_dataframe(data)

        assert len(df) == 2
        assert list(df.columns) == ["year", "value"]
        assert df["year"].tolist() == [2020, 2021]
        assert df["value"].tolist() == [100, 150]
