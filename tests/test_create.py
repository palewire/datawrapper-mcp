"""Tests for the create_chart handler's own error handling."""

from unittest.mock import MagicMock, patch

import pytest

from datawrapper_mcp.handlers.create import create_chart


async def test_invalid_chart_config_raises_helpful_value_error():
    """An invalid chart_config should surface a ValueError with guidance,
    not the raw Pydantic validation error."""
    mock_class = MagicMock()
    mock_class.model_validate.side_effect = ValueError("bad field: nope")

    with patch("datawrapper_mcp.handlers.create.CHART_CLASSES", {"bar": mock_class}):
        with pytest.raises(ValueError, match="Invalid chart configuration") as exc_info:
            await create_chart(
                {
                    "data": [{"a": 1}],
                    "chart_type": "bar",
                    "chart_config": {"nope": True},
                }
            )

    assert "get_chart_schema" in str(exc_info.value)
    assert "bar" in str(exc_info.value)
