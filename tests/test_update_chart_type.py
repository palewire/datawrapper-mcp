"""Test that update_chart properly handles chart_type field during validation."""

from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_update_includes_chart_type_in_validation(mock_api_token):
    """Test that chart_type is included when validating merged config.

    This test verifies the fix for the issue where Pydantic validation
    would fail with "Object has no attribute 'type'" because chart_type
    was excluded from the merged config but is required for validation.
    """
    from datawrapper_mcp.handlers.update import update_chart

    # Mock get_chart to return a ColumnChart instance
    with patch("datawrapper_mcp.handlers.update.get_chart") as mock_get_chart:
        mock_chart = MagicMock()
        mock_chart.chart_id = "test123"
        mock_chart.chart_type = "column-chart"

        # Mock model_dump to return current config without chart_type
        mock_chart.model_dump.return_value = {
            "title": "Original Title",
            "intro": "Original intro",
        }

        mock_chart.update = MagicMock()
        mock_chart.get_editor_url.return_value = (
            "https://app.datawrapper.de/edit/test123/visualize#refine"
        )

        mock_get_chart.return_value = mock_chart

        # Mock type() to return a chart class
        with patch("datawrapper_mcp.handlers.update.type") as mock_type:
            mock_chart_class = MagicMock()
            mock_type.return_value = mock_chart_class

            # Mock model_validate to verify chart_type is included
            validated_chart = MagicMock()
            validated_chart.model_dump.return_value = {
                "title": "Updated Title",
                "intro": "Original intro",
            }
            mock_chart_class.model_validate.return_value = validated_chart

            arguments = {
                "chart_id": "test123",
                "chart_config": {
                    "title": "Updated Title",
                },
            }

            result = await update_chart(arguments)

            # Verify model_validate was called
            mock_chart_class.model_validate.assert_called_once()

            # Verify chart_type was included in the merged config passed to model_validate
            call_args = mock_chart_class.model_validate.call_args[0][0]
            assert "chart_type" in call_args, (
                "chart_type must be included in validation"
            )
            assert call_args["chart_type"] == "column-chart", (
                "chart_type value must match original"
            )

            # Verify update was successful
            assert len(result) > 0
            assert result[0].type == "text"
            assert "updated successfully" in result[0].text.lower()


@pytest.mark.asyncio
async def test_update_excludes_chart_type_from_setattr(mock_api_token):
    """Test that chart_type is not updated via setattr after validation.

    Even though chart_type is included for validation, it should not be
    set on the chart instance since it cannot be changed after creation.
    This test verifies that the exclude parameter in model_dump() works correctly.
    """
    from datawrapper_mcp.handlers.update import update_chart

    with patch("datawrapper_mcp.handlers.update.get_chart") as mock_get_chart:
        mock_chart = MagicMock()
        mock_chart.chart_id = "test123"
        mock_chart.chart_type = "column-chart"
        mock_chart.model_dump.return_value = {"title": "Test"}
        mock_chart.update = MagicMock()
        mock_chart.get_editor_url.return_value = (
            "https://app.datawrapper.de/edit/test123/visualize#refine"
        )

        mock_get_chart.return_value = mock_chart

        with patch("datawrapper_mcp.handlers.update.type") as mock_type:
            mock_chart_class = MagicMock()
            mock_type.return_value = mock_chart_class

            validated_chart = MagicMock()

            # Mock model_dump to respect the exclude parameter
            # When called with exclude={"data", "chart_type", "chart_id"},
            # it should NOT include chart_type (matching Pydantic's actual behavior)
            def mock_model_dump(exclude=None, **kwargs):
                result = {
                    "title": "New Title",
                    "chart_type": "column-chart",
                }
                if exclude:
                    for key in exclude:
                        result.pop(key, None)
                return result

            validated_chart.model_dump = mock_model_dump
            mock_chart_class.model_validate.return_value = validated_chart

            # Track setattr calls
            setattr_calls = []
            original_setattr = setattr

            def track_setattr(obj, name, value):
                if obj is mock_chart:
                    setattr_calls.append((name, value))
                return original_setattr(obj, name, value)

            with patch("builtins.setattr", side_effect=track_setattr):
                arguments = {
                    "chart_id": "test123",
                    "chart_config": {"title": "New Title"},
                }

                await update_chart(arguments)

            # Verify chart_type was NOT set via setattr
            setattr_names = [name for name, _ in setattr_calls]
            assert "chart_type" not in setattr_names, (
                "chart_type should not be updated via setattr"
            )

            # Verify title WAS set
            assert "title" in setattr_names, "title should be updated via setattr"
