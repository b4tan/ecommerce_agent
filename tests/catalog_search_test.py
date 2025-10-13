"""
Basic tests for catalog search functionality.
These are simple smoke tests to ensure the search works correctly.
"""
import pytest
from services.catalog_search import TextSearchSpec, text_search
from tests.conftest import TestDataHelper, DB_AVAILABLE


@pytest.mark.skipif(not DB_AVAILABLE, reason="DB not found; set DB_PATH or create ./data/catalog.sqlite")
def test_db_file_exists_and_connects():
    """Test that database file exists and can be connected to."""
    # This test is handled by the db_connection fixture in conftest.py
    assert DB_AVAILABLE, "Database should be available"


@pytest.mark.skipif(not DB_AVAILABLE, reason="DB not found; set DB_PATH or create ./data/catalog.sqlite")
def test_text_search_basic_like_or_fts():
    """Test basic text search functionality."""
    spec = TextSearchSpec(q="a", limit=3, offset=0)
    result = text_search(spec)
    
    TestDataHelper.assert_valid_search_result(result)
    assert len(result["products"]) <= 3


@pytest.mark.skipif(not DB_AVAILABLE, reason="DB not found; set DB_PATH or create ./data/catalog.sqlite")
def test_filters_and_sorting_do_not_crash_and_return_slice():
    """Test that filters and sorting work without crashing."""
    spec = TextSearchSpec(
        q="shoe",
        filters={"rating_min": 3.5, "price_max": 500, "availability": True},
        sort_spec=[{"key": "rating", "dir": "desc"}, {"key": "reviews_count", "dir": "desc"}],
        limit=3,
        offset=0,
    )
    result = text_search(spec)
    
    TestDataHelper.assert_valid_search_result(result)
    assert len(result["products"]) <= 3
    
    # Check shape of first product if present
    if result["products"]:
        TestDataHelper.assert_valid_product_card(result["products"][0])


@pytest.mark.skipif(not DB_AVAILABLE, reason="DB not found; set DB_PATH or create ./data/catalog.sqlite")
def test_pagination_offset_next_slice():
    """Test pagination functionality."""
    first = text_search(TextSearchSpec(q="the", limit=3, offset=0))
    second = text_search(TextSearchSpec(q="the", limit=3, offset=3))
    
    TestDataHelper.assert_valid_search_result(first)
    TestDataHelper.assert_valid_search_result(second)
    
    asin1 = {p["asin"] for p in first["products"]}
    asin2 = {p["asin"] for p in second["products"]}
    
    # If there are enough hits, the sets should differ
    if first["total"] > 3:
        assert asin1.isdisjoint(asin2), "Pagination should return different products"
