"""Shared pytest fixtures for datawrapper-mcp tests."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from datawrapper import BarChart


@pytest.fixture
def mock_api_token(monkeypatch):
    """Mock the API token environment variable."""
    monkeypatch.setenv("DATAWRAPPER_ACCESS_TOKEN", "test_token_12345")
    return "test_token_12345"


@pytest.fixture
def sample_data():
    """Provide sample chart data."""
    return [
        {"category": "A", "value": 100},
        {"category": "B", "value": 150},
        {"category": "C", "value": 200},
    ]


@pytest.fixture
def sample_dataframe(sample_data):
    """Provide sample data as a DataFrame."""
    return pd.DataFrame(sample_data)


@pytest.fixture
def mock_chart():
    """Create a mock chart instance."""
    chart = MagicMock(spec=BarChart)
    chart.chart_id = "test123"
    chart.chart_type = "d3-bars"
    chart.title = "Test Chart"
    chart.intro = "Test intro"
    chart.byline = "Test Author"
    chart.source_name = "Test Source"
    chart.source_url = "https://example.com"
    chart.model_dump.return_value = {
        "title": "Test Chart",
        "intro": "Test intro",
        "byline": "Test Author",
        "source_name": "Test Source",
        "source_url": "https://example.com",
    }
    chart.get_editor_url.return_value = "https://app.datawrapper.de/chart/test123/edit"
    chart.get_public_url.return_value = "https://datawrapper.dwcdn.net/test123/"
    return chart


@pytest.fixture
def mock_get_chart(mock_chart):
    """Mock the get_chart factory function in all handler modules."""
    # Patch get_chart in all handler modules that import it
    patches = [
        patch("datawrapper_mcp.handlers.publish.get_chart", return_value=mock_chart),
        patch("datawrapper_mcp.handlers.retrieve.get_chart", return_value=mock_chart),
        patch("datawrapper_mcp.handlers.update.get_chart", return_value=mock_chart),
        patch("datawrapper_mcp.handlers.delete.get_chart", return_value=mock_chart),
        patch("datawrapper_mcp.handlers.export.get_chart", return_value=mock_chart),
    ]

    # Start all patches
    mocks = [p.start() for p in patches]

    # Yield the first mock (they all return the same mock_chart)
    yield mocks[0]

    # Stop all patches
    for p in patches:
        p.stop()


@pytest.fixture
def mock_bar_chart_class():
    """Mock the BarChart class for validation."""
    with patch("datawrapper_mcp.config.BarChart") as mock_class:
        # Create a mock instance that will be returned by model_validate
        mock_instance = MagicMock(spec=BarChart)
        mock_instance.chart_id = None
        mock_instance.title = "Test Chart"
        mock_instance.model_dump.return_value = {
            "title": "Test Chart",
            "intro": "",
            "byline": "",
        }

        # Make model_validate return the mock instance
        mock_class.model_validate.return_value = mock_instance

        yield mock_class


@pytest.fixture
def no_api_token(monkeypatch):
    """Remove the API token environment variable."""
    monkeypatch.delenv("DATAWRAPPER_ACCESS_TOKEN", raising=False)
