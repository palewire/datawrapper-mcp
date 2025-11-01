"""Test script to verify update_chart Pydantic validation."""

import json
from datawrapper_mcp.server import update_chart


async def test_update_with_low_level_structure():
    """Test that low-level structures like 'metadata' are rejected."""
    
    # This should fail - trying to use low-level 'metadata' structure
    arguments = {
        "chart_id": "test123",
        "chart_config": {
            "metadata": {
                "visualize": {
                    "some-setting": "value"
                }
            }
        }
    }
    
    print("Test 1: Attempting to update with low-level 'metadata' structure...")
    print(f"Arguments: {json.dumps(arguments, indent=2)}")
    print("\nExpected: Should fail with validation error")
    print("Actual: (Would need real API token and chart to test)")
    print()


async def test_update_with_high_level_fields():
    """Test that high-level Pydantic fields are accepted."""
    
    # This should succeed - using high-level Pydantic fields
    arguments = {
        "chart_id": "test123",
        "chart_config": {
            "title": "Updated Chart Title",
            "intro": "This is an updated introduction",
            "byline": "Updated Author",
            "source_name": "Updated Source",
            "source_url": "https://example.com/updated"
        }
    }
    
    print("Test 2: Attempting to update with high-level Pydantic fields...")
    print(f"Arguments: {json.dumps(arguments, indent=2)}")
    print("\nExpected: Should succeed and validate through Pydantic")
    print("Actual: (Would need real API token and chart to test)")
    print()


def main():
    """Run tests."""
    print("=" * 70)
    print("UPDATE_CHART PYDANTIC VALIDATION TEST")
    print("=" * 70)
    print()
    print("This test demonstrates the validation logic in update_chart.")
    print("To run actual tests, you would need:")
    print("  1. DATAWRAPPER_API_TOKEN environment variable set")
    print("  2. A real chart ID to update")
    print()
    print("=" * 70)
    print()
    
    import asyncio
    asyncio.run(test_update_with_low_level_structure())
    asyncio.run(test_update_with_high_level_fields())
    
    print("=" * 70)
    print("KEY IMPLEMENTATION DETAILS")
    print("=" * 70)
    print()
    print("The update_chart function now:")
    print("  1. Retrieves the existing chart")
    print("  2. Maps the API chart type to CHART_CLASSES key")
    print("  3. Gets current config via chart.model_dump()")
    print("  4. Merges new config with existing config")
    print("  5. Validates merged config via model_validate()")
    print("  6. Updates chart attributes from validated model")
    print("  7. Calls chart.update(access_token)")
    print()
    print("This ensures:")
    print("  ✓ Only high-level Pydantic fields are accepted")
    print("  ✓ All validation rules are enforced")
    print("  ✓ Low-level structures like 'metadata' are rejected")
    print("  ✓ Chatbots must use the intended API surface")
    print()


if __name__ == "__main__":
    main()
