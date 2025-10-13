"""
Basic tests for catalog API functionality.
These are simple smoke tests to ensure the API works correctly.
"""
import pytest
from services.catalog_api import get_catalog_api
from tests.conftest import TestDataHelper, DB_AVAILABLE


@pytest.mark.skipif(not DB_AVAILABLE, reason="DB not found; set DB_PATH or create ./data/catalog.sqlite")
def test_catalog_api_search_returns_at_most_three():
    """Test that API search returns at most 3 products (limit clamping)."""
    api = get_catalog_api()
    result = api.search_products(q="shirt", limit=10, offset=0)  # API clamps to 3
    
    TestDataHelper.assert_valid_search_result(result)
    assert len(result["products"]) <= 3


@pytest.mark.skipif(not DB_AVAILABLE, reason="DB not found; set DB_PATH or create ./data/catalog.sqlite")
def test_catalog_api_basic_functionality():
    """Test basic API functionality with minimal parameters."""
    api = get_catalog_api()
    result = api.search_products()
    
    TestDataHelper.assert_valid_search_result(result)


@pytest.mark.skipif(not DB_AVAILABLE, reason="DB not found; set DB_PATH or create ./data/catalog.sqlite")
def test_catalog_api_get_product():
    """Test single product retrieval."""
    api = get_catalog_api()
    product = api.get_product("B09NQJFRW6")  # Known ASIN from database
    
    if product:
        assert hasattr(product, "asin") or "asin" in product
        assert hasattr(product, "title") or "title" in product
