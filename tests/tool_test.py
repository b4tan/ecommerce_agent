"""
Basic tests for the product_search tool functionality.
These are simple smoke tests to ensure the tool works correctly.
"""
import pytest
from backend.agent.tools import product_search
from tests.conftest import TestDataHelper, DB_AVAILABLE


@pytest.mark.skipif(not DB_AVAILABLE, reason="DB not found; set DB_PATH or create ./data/catalog.sqlite")
def test_product_search_tool_happy_path():
    """Test the product search tool with a typical use case."""
    payload = TestDataHelper.create_valid_payload(
        q="running",
        filters={"rating_min": 3.5, "availability": True},
        sort_spec=[{"key": "rating", "dir": "desc"}],
        limit=12,  # tool clamps to 3
        offset=0
    )
    
    result = product_search.invoke(payload)
    TestDataHelper.assert_valid_search_result(result)
    assert len(result["products"]) <= 3
    
    if result["products"]:
        TestDataHelper.assert_valid_product_card(result["products"][0])


@pytest.mark.skipif(not DB_AVAILABLE, reason="DB not found; set DB_PATH or create ./data/catalog.sqlite")
def test_product_search_tool_basic_functionality():
    """Test basic tool functionality with minimal parameters."""
    payload = TestDataHelper.create_valid_payload()
    result = product_search.invoke(payload)
    
    TestDataHelper.assert_valid_search_result(result)


@pytest.mark.skipif(not DB_AVAILABLE, reason="DB not found; set DB_PATH or create ./data/catalog.sqlite")
def test_product_search_tool_error_handling():
    """Test tool error handling with invalid input."""
    # Test with None payload - should raise ValidationError
    with pytest.raises(Exception):
        product_search.invoke(None)
    
    # Test with empty payload - should raise ValidationError
    with pytest.raises(Exception):
        product_search.invoke({})
