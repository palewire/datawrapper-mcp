"""Tests for data validation and error messages in json_to_dataframe."""

import pytest

from datawrapper_mcp.utils import json_to_dataframe


class TestValidDataFormats:
    """Test that valid data formats are accepted."""

    def test_list_of_dicts(self):
        """Test list of records format."""
        data = [{"year": 2020, "value": 100}, {"year": 2021, "value": 150}]
        df = json_to_dataframe(data)
        assert len(df) == 2
        assert list(df.columns) == ["year", "value"]

    def test_dict_of_arrays(self):
        """Test dict of arrays format."""
        data = {"year": [2020, 2021], "value": [100, 150]}
        df = json_to_dataframe(data)
        assert len(df) == 2
        assert list(df.columns) == ["year", "value"]

    def test_json_string_list(self):
        """Test JSON string with list format."""
        data = '[{"year": 2020, "value": 100}, {"year": 2021, "value": 150}]'
        df = json_to_dataframe(data)
        assert len(df) == 2
        assert list(df.columns) == ["year", "value"]

    def test_json_string_dict(self):
        """Test JSON string with dict format."""
        data = '{"year": [2020, 2021], "value": [100, 150]}'
        df = json_to_dataframe(data)
        assert len(df) == 2
        assert list(df.columns) == ["year", "value"]

    def test_large_dataset(self):
        """Test that large datasets are supported."""
        data = [{"id": i, "value": i * 10} for i in range(1000)]
        df = json_to_dataframe(data)
        assert len(df) == 1000


class TestFilePathDetection:
    """Test that non-existent file paths are handled gracefully."""

    def test_nonexistent_csv_file_path(self):
        """Test that non-existent CSV file paths fall through to JSON parsing."""
        with pytest.raises(ValueError) as exc_info:
            json_to_dataframe("data.csv")

        error_msg = str(exc_info.value)
        # Non-existent file paths are treated as invalid JSON strings
        assert "Invalid JSON string" in error_msg

    def test_nonexistent_json_file_path(self):
        """Test that non-existent JSON file paths fall through to JSON parsing."""
        with pytest.raises(ValueError) as exc_info:
            json_to_dataframe("data.json")

        error_msg = str(exc_info.value)
        assert "Invalid JSON string" in error_msg

    def test_nonexistent_absolute_path(self):
        """Test that non-existent absolute paths fall through to JSON parsing."""
        with pytest.raises(ValueError) as exc_info:
            json_to_dataframe("/path/to/data.csv")

        error_msg = str(exc_info.value)
        assert "Invalid JSON string" in error_msg

    def test_nonexistent_windows_path(self):
        """Test that non-existent Windows paths fall through to JSON parsing."""
        with pytest.raises(ValueError) as exc_info:
            json_to_dataframe("C:\\Users\\data.csv")

        error_msg = str(exc_info.value)
        assert "Invalid JSON string" in error_msg


class TestCSVStringDetection:
    """Test that CSV strings are detected and rejected with helpful messages."""

    def test_csv_string(self):
        """Test that CSV strings are rejected."""
        csv_data = "year,value\n2020,100\n2021,150"
        with pytest.raises(ValueError) as exc_info:
            json_to_dataframe(csv_data)

        error_msg = str(exc_info.value)
        assert "CSV strings are not supported" in error_msg
        assert "save to a file first" in error_msg
        assert "Example:" in error_msg

    def test_tab_separated(self):
        """Test that tab-separated strings are rejected."""
        tsv_data = "year\tvalue\n2020\t100\n2021\t150"
        with pytest.raises(ValueError) as exc_info:
            json_to_dataframe(tsv_data)

        error_msg = str(exc_info.value)
        # Tab-separated data doesn't have commas, so it falls through to JSON parsing
        assert "Invalid JSON string" in error_msg


class TestInvalidJSON:
    """Test that invalid JSON strings provide helpful error messages."""

    def test_malformed_json(self):
        """Test that malformed JSON is rejected with helpful message."""
        with pytest.raises(ValueError) as exc_info:
            json_to_dataframe('{"year": [2020, 2021]')  # Missing closing brace

        error_msg = str(exc_info.value)
        assert "Invalid JSON string" in error_msg
        assert "Expected one of" in error_msg

    def test_invalid_json_syntax(self):
        """Test that invalid JSON syntax is rejected."""
        with pytest.raises(ValueError) as exc_info:
            json_to_dataframe("not json at all")

        error_msg = str(exc_info.value)
        assert "Invalid JSON string" in error_msg


class TestEmptyData:
    """Test that empty data is rejected with helpful messages."""

    def test_empty_list(self):
        """Test that empty lists are rejected."""
        with pytest.raises(ValueError) as exc_info:
            json_to_dataframe([])

        error_msg = str(exc_info.value)
        assert "Data list is empty" in error_msg
        assert "at least one row" in error_msg

    def test_empty_dict(self):
        """Test that empty dicts are rejected."""
        with pytest.raises(ValueError) as exc_info:
            json_to_dataframe({})

        error_msg = str(exc_info.value)
        assert "Data dict is empty" in error_msg
        assert "at least one column" in error_msg


class TestInvalidDataStructures:
    """Test that invalid data structures are rejected with helpful messages."""

    def test_list_of_non_dicts(self):
        """Test that lists containing non-dicts are rejected."""
        with pytest.raises(ValueError) as exc_info:
            json_to_dataframe([1, 2, 3])

        error_msg = str(exc_info.value)
        assert "List format must contain dictionaries" in error_msg
        assert "Expected format:" in error_msg
        assert "int" in error_msg

    def test_dict_with_non_list_values(self):
        """Test that dicts with non-list values are rejected."""
        with pytest.raises(ValueError) as exc_info:
            json_to_dataframe({"year": 2020, "value": 100})

        error_msg = str(exc_info.value)
        assert "Dict format must have lists as values" in error_msg
        assert "Expected format:" in error_msg

    def test_unsupported_type(self):
        """Test that unsupported types are rejected."""
        with pytest.raises(ValueError) as exc_info:
            json_to_dataframe(12345)  # type: ignore[arg-type]

        error_msg = str(exc_info.value)
        assert "Unsupported data type: int" in error_msg
        assert "Data must be one of:" in error_msg


class TestErrorMessageQuality:
    """Test that error messages are helpful and actionable."""

    def test_error_includes_examples(self):
        """Test that error messages include examples."""
        with pytest.raises(ValueError) as exc_info:
            json_to_dataframe([1, 2, 3])  # Use invalid list instead of file path

        error_msg = str(exc_info.value)
        # Check for "Expected format:" which shows examples
        assert "Expected format:" in error_msg or "example" in error_msg.lower()

    def test_error_suggests_solution(self):
        """Test that error messages suggest solutions."""
        with pytest.raises(ValueError) as exc_info:
            json_to_dataframe("year,value\n2020,100")

        error_msg = str(exc_info.value)
        assert "parse" in error_msg.lower() or "convert" in error_msg.lower()

    def test_error_shows_correct_format(self):
        """Test that error messages show correct format."""
        with pytest.raises(ValueError) as exc_info:
            json_to_dataframe([1, 2, 3])

        error_msg = str(exc_info.value)
        assert '{"' in error_msg or "[{" in error_msg  # Shows dict/list format
