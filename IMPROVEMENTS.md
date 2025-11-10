# datawrapper-mcp Improvement Ideas

This document contains improvement ideas identified through comprehensive code analysis using sequential thinking. These suggestions are organized by priority and impact.

## 🎯 HIGH PRIORITY IMPROVEMENTS

### 1. ✅ Standardize Return Types Across All Tools (COMPLETED)

**Status**: ✅ Completed on 2025-01-10

**What Was Done**:
- Updated all 7 tools in `server.py` to return `Sequence[TextContent | ImageContent]`
- Removed `.text` extraction logic from all tools
- Tools now pass through handler results directly
- Wrapped exceptions in `TextContent` for consistent error handling
- All 69 tests pass without modification (tests target handlers, not tools)
- Updated documentation in README.md and .clinerules

**Impact**: High - Achieved protocol compliance and API consistency

**Proposed Solution**:
```python
# All tools should return Sequence[TextContent | ImageContent]
# Example transformation:

# Before (in server.py):
@mcp.tool()
def create_chart(...) -> str:
    return create_chart_handler(...)

# After:
@mcp.tool()
def create_chart(...) -> Sequence[TextContent | ImageContent]:
    result = create_chart_handler(...)
    return [TextContent(type="text", text=result)]
```

**Implementation Steps**:
1. Update all tool return type annotations in `server.py`
2. Wrap string results in `[TextContent(type="text", text=result)]`
3. Keep `export_chart_png` as-is (already correct)
4. Update tests to verify return type structure
5. Update documentation to reflect new return types

**Effort**: Low-Medium (2-3 hours)

---

### 2. Enhance Error Messages with Actionable Guidance

**Current Issue**: Generic error messages don't guide users to solutions
- Users don't know how to fix issues
- Increases support burden
- Poor developer experience

**Impact**: High - Directly affects user experience

**Proposed Solution**:
```python
# Add error codes and enhanced messages

class DatawrapperMCPError(Exception):
    """Base exception with error codes and guidance"""
    def __init__(self, code: str, message: str, guidance: str):
        self.code = code
        self.message = message
        self.guidance = guidance
        super().__init__(f"[{code}] {message}\n\nHow to fix: {guidance}")

# Example usage:
def get_api_token() -> str:
    token = os.getenv("DATAWRAPPER_ACCESS_TOKEN")
    if not token:
        raise DatawrapperMCPError(
            code="DW_MISSING_TOKEN",
            message="DATAWRAPPER_ACCESS_TOKEN environment variable not set",
            guidance="Get an API token at https://app.datawrapper.de/account/api-tokens and set it as an environment variable"
        )
    return token

# Validation errors:
raise DatawrapperMCPError(
    code="DW_INVALID_CHART_TYPE",
    message=f"Chart type '{chart_type}' not supported",
    guidance=f"Supported types: {', '.join(CHART_CLASSES.keys())}. Use get_chart_schema to explore options."
)
```

**Error Codes to Add**:
- `DW_MISSING_TOKEN`: API token not configured
- `DW_INVALID_TOKEN`: API token rejected by Datawrapper
- `DW_INVALID_CHART_TYPE`: Unsupported chart type
- `DW_VALIDATION_ERROR`: Pydantic validation failed
- `DW_INVALID_DATA_FORMAT`: Data format not recognized
- `DW_CHART_NOT_FOUND`: Chart ID doesn't exist
- `DW_API_ERROR`: Datawrapper API error
- `DW_NETWORK_ERROR`: Network connectivity issue

**Implementation Steps**:
1. Create custom exception classes with error codes
2. Update all error handling to use new exceptions
3. Add guidance strings for each error type
4. Update tests to verify error messages
5. Document error codes in README

**Effort**: Medium (3-4 hours)

---

### 3. Add Input Validation Before API Calls

**Current Issue**: No validation for inputs before making API calls
- Invalid chart_ids cause unnecessary API calls
- Unclear error messages from API
- Wasted network requests

**Impact**: Medium-High - Improves performance and error clarity

**Proposed Solution**:
```python
# Add to utils.py:
import re

def validate_chart_id(chart_id: str) -> None:
    """Validate chart ID format before API calls"""
    if not chart_id:
        raise DatawrapperMCPError(
            code="DW_INVALID_CHART_ID",
            message="Chart ID cannot be empty",
            guidance="Provide a valid chart ID from a previously created chart"
        )

    # Datawrapper chart IDs are typically alphanumeric
    if not re.match(r'^[a-zA-Z0-9]+$', chart_id):
        raise DatawrapperMCPError(
            code="DW_INVALID_CHART_ID",
            message=f"Invalid chart ID format: {chart_id}",
            guidance="Chart IDs should contain only letters and numbers"
        )

def validate_chart_type(chart_type: str) -> None:
    """Validate chart type against supported types"""
    if chart_type not in CHART_CLASSES:
        raise DatawrapperMCPError(
            code="DW_INVALID_CHART_TYPE",
            message=f"Unsupported chart type: {chart_type}",
            guidance=f"Supported types: {', '.join(CHART_CLASSES.keys())}"
        )

# Usage in handlers:
def update_chart_handler(chart_id: str, ...):
    validate_chart_id(chart_id)
    # ... rest of implementation
```

**Validations to Add**:
- Chart ID format validation
- Chart type validation against CHART_CLASSES
- Data format validation (before conversion)
- Configuration key validation (warn on unknown keys)
- File path validation (exists, readable)

**Implementation Steps**:
1. Add validation functions to utils.py
2. Update all handlers to call validators
3. Add tests for validation logic
4. Document validation rules

**Effort**: Low-Medium (2-3 hours)

---

## 📊 MEDIUM PRIORITY IMPROVEMENTS

### 4. Implement Resource Caching for Static Schemas

**Current Issue**: `chart_types_resource` regenerates schemas on every request
- Schemas are static (only change when CHART_CLASSES changes)
- Unnecessary computation for unchanging data
- Increased latency for schema requests

**Impact**: Medium - Performance optimization

**Proposed Solution**:
```python
# Add to server.py:
from functools import lru_cache

@lru_cache(maxsize=1)
def _generate_chart_schemas() -> dict:
    """Generate and cache chart type schemas"""
    schemas = {}
    for chart_type, chart_class in CHART_CLASSES.items():
        schemas[chart_type] = chart_class.model_json_schema()
    return schemas

@mcp.resource("datawrapper://chart-types")
def chart_types_resource() -> str:
    """List of available Datawrapper chart types and their Pydantic schemas."""
    schemas = _generate_chart_schemas()
    return json.dumps(schemas, indent=2)
```

**Implementation Steps**:
1. Add caching decorator to schema generation
2. Test cache behavior
3. Add cache invalidation if needed (probably not)
4. Measure performance improvement

**Effort**: Low (1 hour)

---

### 5. Add Comprehensive Docstring Examples

**Current Issue**: Docstrings lack concrete usage examples
- Developers must guess at proper usage patterns
- Unclear what valid inputs look like
- No styling examples

**Impact**: Medium - Improves developer experience

**Proposed Solution**:
```python
@mcp.tool()
def create_chart(
    data: str | list | dict,
    chart_type: str,
    chart_config: dict,
) -> Sequence[TextContent | ImageContent]:
    """Create a Datawrapper chart with full control using Pydantic models.

    Examples:
        Basic line chart:
        >>> data = [
        ...     {"date": "2024-01", "sales": 100, "profit": 20},
        ...     {"date": "2024-02", "sales": 150, "profit": 30}
        ... ]
        >>> config = {
        ...     "title": "Monthly Sales",
        ...     "intro": "Sales and profit trends",
        ...     "source_name": "Company Data",
        ...     "source_url": "https://example.com"
        ... }
        >>> create_chart(data, "line", config)

        Styled line chart with colors:
        >>> config = {
        ...     "title": "Styled Chart",
        ...     "color_category": {
        ...         "sales": "#1d81a2",
        ...         "profit": "#15607a"
        ...     },
        ...     "lines": [
        ...         {"column": "sales", "width": "style2", "interpolation": "curved"},
        ...         {"column": "profit", "width": "style1", "interpolation": "linear"}
        ...     ]
        ... }
        >>> create_chart(data, "line", config)

    Args:
        data: Chart data in one of these formats:
            - List of records: [{"col": val}, ...]
            - Dict of arrays: {"col": [vals]}
            - JSON string of above formats
            - File path to CSV or JSON (for large datasets only)
        chart_type: One of: bar, line, area, arrow, column,
                   multiple_column, scatter, stacked_bar
        chart_config: Complete chart configuration dict with Pydantic fields

    Returns:
        Chart ID and editor URL
    """
```

**Implementation Steps**:
1. Add detailed examples to all tool docstrings
2. Include common styling patterns
3. Show data format variations
4. Add error handling examples
5. Update README with examples

**Effort**: Medium (3-4 hours)

---

### 6. Create Troubleshooting Guide

**Current Issue**: No centralized troubleshooting documentation
- Users struggle with common issues
- Repeated support questions
- No debugging guidance

**Impact**: Medium - Reduces support burden

**Proposed Solution**:
Create `TROUBLESHOOTING.md` with sections:

```markdown
# Troubleshooting Guide

## Common Issues

### "DATAWRAPPER_ACCESS_TOKEN environment variable not set"
**Cause**: API token not configured
**Solution**:
1. Get token at https://app.datawrapper.de/account/api-tokens
2. Set environment variable: `export DATAWRAPPER_ACCESS_TOKEN=your_token`
3. Restart the MCP server

### "Validation error for [field]"
**Cause**: Invalid chart configuration
**Solution**:
1. Use `get_chart_schema` to see valid options
2. Check field types and enum values
3. Refer to https://datawrapper.readthedocs.io/en/latest/

### "Invalid data format"
**Cause**: Data not in expected format
**Solution**:
Valid formats:
- List of dicts: [{"col": val}, ...]
- Dict of arrays: {"col": [vals]}
- JSON string of above
- File path to CSV/JSON

### Chart not displaying correctly
**Cause**: Missing or incorrect styling configuration
**Solution**:
1. Use `get_chart_schema` to explore options
2. Check color_category, lines, axes settings
3. Verify data column names match config

## Debugging Tips

### Enable verbose logging
[Instructions for logging configuration]

### Inspect chart configuration
[How to retrieve and examine chart config]

### Test with minimal example
[Minimal working example]
```

**Implementation Steps**:
1. Create TROUBLESHOOTING.md
2. Document common errors and solutions
3. Add debugging tips
4. Include minimal working examples
5. Link from README

**Effort**: Medium (2-3 hours)

---

### 7. Add Rate Limiting Awareness and Handling

**Current Issue**: No handling or documentation of Datawrapper API rate limits
- Unexpected failures during high-volume operations
- No retry logic for rate limit errors
- Users don't know limits exist

**Impact**: Medium - Prevents production issues

**Proposed Solution**:
```python
# Add to utils.py:
import time
from functools import wraps

def with_retry(max_retries=3, backoff_factor=2):
    """Decorator to retry API calls with exponential backoff"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if "rate limit" in str(e).lower() and attempt < max_retries - 1:
                        wait_time = backoff_factor ** attempt
                        logger.warning(f"Rate limited, retrying in {wait_time}s")
                        time.sleep(wait_time)
                    else:
                        raise
            return func(*args, **kwargs)
        return wrapper
    return decorator

# Usage:
@with_retry(max_retries=3)
def create_chart_handler(...):
    # ... implementation
```

**Documentation to Add**:
- Datawrapper API rate limits (if documented)
- Retry behavior and configuration
- Best practices for bulk operations
- Recommended delays between operations

**Implementation Steps**:
1. Research Datawrapper API rate limits
2. Add retry decorator with exponential backoff
3. Document rate limits in README
4. Add configuration for retry behavior
5. Test retry logic

**Effort**: Medium (3-4 hours)

---

## 🔧 LOW PRIORITY IMPROVEMENTS

### 8. Add Telemetry and Metrics Collection

**Current Issue**: No visibility into usage patterns or performance
- Cannot identify bottlenecks
- No usage analytics
- Cannot track success/failure rates

**Impact**: Low-Medium - Useful for optimization

**Proposed Solution**:
```python
# Add metrics collection:
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class OperationMetric:
    operation: str
    chart_type: Optional[str]
    duration_ms: float
    success: bool
    error_code: Optional[str]
    timestamp: datetime

class MetricsCollector:
    def __init__(self):
        self.metrics: list[OperationMetric] = []

    def record(self, metric: OperationMetric):
        self.metrics.append(metric)

    def get_stats(self) -> dict:
        """Get aggregated statistics"""
        total = len(self.metrics)
        successful = sum(1 for m in self.metrics if m.success)

        return {
            "total_operations": total,
            "success_rate": successful / total if total > 0 else 0,
            "operations_by_type": self._count_by_field("operation"),
            "chart_types": self._count_by_field("chart_type"),
            "error_codes": self._count_by_field("error_code"),
            "avg_duration_ms": sum(m.duration_ms for m in self.metrics) / total if total > 0 else 0
        }

    def _count_by_field(self, field: str) -> dict:
        counts = {}
        for metric in self.metrics:
            value = getattr(metric, field)
            if value:
                counts[value] = counts.get(value, 0) + 1
        return counts

# Usage in handlers:
metrics = MetricsCollector()

def create_chart_handler(...):
    start = time.time()
    success = False
    error_code = None
    try:
        # ... implementation
        success = True
    except DatawrapperMCPError as e:
        error_code = e.code
        raise
    finally:
        duration = (time.time() - start) * 1000
        metrics.record(OperationMetric(
            operation="create_chart",
            chart_type=chart_type,
            duration_ms=duration,
            success=success,
            error_code=error_code,
            timestamp=datetime.now()
        ))
```

**Metrics to Track**:
- Operation counts by type (create, update, delete, etc.)
- Success/failure rates
- Average operation duration
- Chart type distribution
- Error frequency by code
- Peak usage times

**Implementation Steps**:
1. Create metrics collection module
2. Add metrics recording to all handlers
3. Create metrics export endpoint or file
4. Add metrics visualization (optional)
5. Document metrics format

**Effort**: Medium-High (5-6 hours)

---

### 9. Implement Retry Logic with Exponential Backoff

**Current Issue**: No retry logic for transient failures
- Network glitches cause immediate failures
- No resilience for temporary API issues
- Poor user experience for recoverable errors

**Impact**: Low-Medium - Improves reliability

**Proposed Solution**:
```python
# Enhanced retry decorator with more features:
import time
import random
from functools import wraps
from typing import Callable, Type

def with_exponential_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retryable_exceptions: tuple[Type[Exception], ...] = (Exception,)
):
    """Retry with exponential backoff and jitter"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as e:
                    if attempt == max_retries - 1:
                        raise

                    # Calculate delay with exponential backoff
                    delay = min(base_delay * (exponential_base ** attempt), max_delay)

                    # Add jitter to prevent thundering herd
                    if jitter:
                        delay = delay * (0.5 + random.random() * 0.5)

                    logger.warning(
                        f"Attempt {attempt + 1}/{max_retries} failed: {e}. "
                        f"Retrying in {delay:.2f}s"
                    )
                    time.sleep(delay)

            return func(*args, **kwargs)
        return wrapper
    return decorator

# Usage with specific exceptions:
@with_exponential_backoff(
    max_retries=3,
    retryable_exceptions=(ConnectionError, TimeoutError)
)
def create_chart_handler(...):
    # ... implementation
```

**Features**:
- Exponential backoff with configurable base
- Maximum delay cap
- Jitter to prevent thundering herd
- Selective exception retry
- Detailed logging

**Implementation Steps**:
1. Create retry decorator with all features
2. Identify retryable vs non-retryable errors
3. Apply to appropriate handlers
4. Add configuration options
5. Test retry behavior
6. Document retry policy

**Effort**: Medium (3-4 hours)

---

### 10. Add Batch Operations Support

**Current Issue**: No support for bulk operations
- Must create charts one at a time
- Inefficient for bulk data visualization
- No transaction-like semantics

**Impact**: Low - Nice to have for specific use cases

**Proposed Solution**:
```python
@mcp.tool()
def create_charts_batch(
    charts: list[dict],
) -> Sequence[TextContent | ImageContent]:
    """Create multiple charts in a single operation.

    Args:
        charts: List of chart specifications, each containing:
            - data: Chart data
            - chart_type: Chart type
            - chart_config: Chart configuration

    Returns:
        List of results with chart IDs and URLs

    Example:
        >>> charts = [
        ...     {
        ...         "data": [{"x": 1, "y": 2}],
        ...         "chart_type": "line",
        ...         "chart_config": {"title": "Chart 1"}
        ...     },
        ...     {
        ...         "data": [{"x": 3, "y": 4}],
        ...         "chart_type": "bar",
        ...         "chart_config": {"title": "Chart 2"}
        ...     }
        ... ]
        >>> create_charts_batch(charts)
    """
    results = []
    for i, chart_spec in enumerate(charts):
        try:
            result = create_chart_handler(
                data=chart_spec["data"],
                chart_type=chart_spec["chart_type"],
                chart_config=chart_spec["chart_config"]
            )
            results.append({
                "index": i,
                "success": True,
                "result": result
            })
        except Exception as e:
            results.append({
                "index": i,
                "success": False,
                "error": str(e)
            })

    return [TextContent(
        type="text",
        text=json.dumps(results, indent=2)
    )]
```

**Batch Operations to Add**:
- `create_charts_batch`: Create multiple charts
- `update_charts_batch`: Update multiple charts
- `delete_charts_batch`: Delete multiple charts
- `publish_charts_batch`: Publish multiple charts

**Implementation Steps**:
1. Design batch operation API
2. Implement batch handlers
3. Add error handling (partial success)
4. Add progress reporting
5. Test with various batch sizes
6. Document batch operations

**Effort**: High (6-8 hours)

---

## ✅ STRENGTHS OF CURRENT IMPLEMENTATION

The codebase demonstrates several excellent practices that should be maintained:

1. **Clean Architecture**
   - Well-organized with handlers/, utils.py, config.py separation
   - Clear separation of concerns
   - Modular design

2. **Type Safety**
   - Strong Pydantic integration throughout
   - Type hints on all functions
   - Validation at API boundaries

3. **Test Coverage**
   - Comprehensive unit tests
   - Integration tests for deployment
   - Good test organization

4. **Documentation**
   - Excellent .clinerules file for AI assistant guidance
   - Clear README with setup instructions
   - Contributing guidelines

5. **Security**
   - Proper environment variable usage for API tokens
   - No hardcoded credentials
   - Secure by default

6. **Modern Tooling**
   - Uses FastMCP framework
   - uv for dependency management
   - pre-commit hooks for code quality
   - Docker support for deployment

---

## 📋 RECOMMENDED IMPLEMENTATION ORDER

If implementing these improvements, suggested priority order:

### Phase 1: Foundation (Week 1)
1. **Standardize return types** - Affects all tools, foundational change
2. **Enhance error messages** - Immediate UX improvement
3. **Add input validation** - Prevents common errors

### Phase 2: Robustness (Week 2)
4. **Implement resource caching** - Easy performance win
5. **Add retry logic** - Improves reliability
6. **Document rate limits** - Prevents production issues

### Phase 3: Documentation (Week 3)
7. **Improve docstrings** - Better developer experience
8. **Create troubleshooting guide** - Reduces support burden

### Phase 4: Advanced Features (Week 4+)
9. **Add telemetry** - Usage insights
10. **Batch operations** - Advanced use cases

---

## 🎯 QUICK WINS

If time is limited, these improvements provide the best ROI:

1. **Add input validation** (2-3 hours) - Prevents many errors
2. **Implement resource caching** (1 hour) - Easy performance boost
3. **Enhance error messages** (3-4 hours) - Significantly improves UX

Total: ~6-8 hours for substantial improvements

---

## 📝 NOTES

- All improvements maintain backward compatibility where possible
- Breaking changes should be versioned appropriately
- Each improvement includes test requirements
- Documentation updates are part of each improvement
- Consider user feedback when prioritizing

---

## 🔄 MAINTENANCE

After implementing improvements:

1. Update .clinerules with new patterns
2. Update README with new features
3. Add migration guide if breaking changes
4. Update tests for new functionality
5. Monitor metrics for impact assessment
6. Gather user feedback
7. Iterate based on usage patterns

---

*Document created: 2025-01-07*
*Last updated: 2025-01-07*
*Analysis method: Sequential thinking with comprehensive code review*
