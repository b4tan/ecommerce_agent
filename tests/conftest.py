"""
Test configuration and utilities for the ecommerce agent test suite.
"""
import os
import pytest
import sqlite3
from typing import Dict, Any, List, Optional
from unittest.mock import patch, MagicMock

# Test database path
TEST_DB_PATH = "./data/catalog.sqlite"

@pytest.fixture
def db_connection():
    """Fixture providing a database connection for tests."""
    if not os.path.exists(TEST_DB_PATH):
        pytest.skip(f"Test database not found at {TEST_DB_PATH}")
    
    conn = sqlite3.connect(TEST_DB_PATH)
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()

# Global database availability check for skipif conditions
DB_AVAILABLE = os.path.exists(TEST_DB_PATH)

@pytest.fixture
def sample_product_data():
    """Fixture providing sample product data for testing."""
    return {
        "asin": "B09NQJFRW6",
        "title": "Saucony Men's Kinvara 13 Running Shoe",
        "final_price": 99.99,
        "currency": "USD",
        "rating": 4.6,
        "image_url": "https://example.com/image.jpg",
        "url": "https://example.com/product",
        "brand": "Saucony",
        "department": "Sports",
        "bs_category": "Shoes",
        "is_available": 1,
        "reviews_count": 150
    }

@pytest.fixture
def mock_product_row(sample_product_data):
    """Fixture providing a mock database row for testing."""
    row = MagicMock()
    row.get.side_effect = lambda key: sample_product_data.get(key)
    row.__getitem__.side_effect = lambda key: sample_product_data.get(key)
    return row

@pytest.fixture
def text_search_spec():
    """Fixture providing a basic TextSearchSpec for testing."""
    from services.catalog_search import TextSearchSpec
    return TextSearchSpec(
        q="running shoes",
        filters={"rating_min": 4.0},
        sort_spec=[{"key": "rating", "dir": "desc"}],
        limit=3,
        offset=0
    )

class TestDataHelper:
    """Helper class for creating test data and assertions."""
    
    @staticmethod
    def create_valid_payload(**kwargs) -> Dict[str, Any]:
        """Create a valid tool payload with optional overrides."""
        default_payload = {
            "q": "test query",
            "filters": {"rating_min": 3.5},
            "sort_spec": [{"key": "rating", "dir": "desc"}],
            "limit": 3,
            "offset": 0
        }
        default_payload.update(kwargs)
        return {"payload": default_payload}
    
    @staticmethod
    def assert_valid_search_result(result: Dict[str, Any]) -> None:
        """Assert that a search result has the expected structure."""
        assert isinstance(result, dict), "Result should be a dictionary"
        assert "products" in result, "Result should contain 'products' key"
        assert "total" in result, "Result should contain 'total' key"
        assert isinstance(result["products"], list), "Products should be a list"
        assert isinstance(result["total"], int), "Total should be an integer"
        assert result["total"] >= 0, "Total should be non-negative"
    
    @staticmethod
    def assert_valid_product_card(product: Dict[str, Any]) -> None:
        """Assert that a product card has the expected structure."""
        assert isinstance(product, dict), "Product should be a dictionary"
        assert "asin" in product, "Product should have 'asin'"
        assert "title" in product, "Product should have 'title'"
        assert isinstance(product["asin"], str), "ASIN should be a string"
        assert isinstance(product["title"], str), "Title should be a string"
        assert product["asin"], "ASIN should not be empty"
        assert product["title"], "Title should not be empty"

# Test categories for parameterized tests
SEARCH_QUERIES = [
    "running shoes",
    "laptop",
    "phone",
    "book",
    "",  # Empty query
    "nonexistent_product_xyz",  # Query with no results
]

FILTER_COMBINATIONS = [
    {},  # No filters
    {"rating_min": 4.0},
    {"rating_min": 3.0, "rating_max": 5.0},
    {"price_min": 10.0, "price_max": 100.0},
    {"availability": True},
    {"brand_in": ["Nike", "Adidas"]},
    {"rating_min": 4.0, "availability": True, "price_max": 50.0},  # Multiple filters
]

SORT_SPECS = [
    None,  # Default sorting
    [{"key": "rating", "dir": "desc"}],
    [{"key": "final_price", "dir": "asc"}],
    [{"key": "reviews_count", "dir": "desc"}],
    [{"key": "rating", "dir": "desc"}, {"key": "reviews_count", "dir": "desc"}],  # Multiple sorts
]

INVALID_INPUTS = [
    None,
    {},
    {"invalid_key": "value"},
    {"q": None},
    {"filters": "not_a_dict"},
    {"sort_spec": "not_a_list"},
    {"limit": "not_a_number"},
    {"offset": "not_a_number"},
    {"limit": -1},
    {"limit": 0},
    {"offset": -1},
    {"limit": 1000},  # Too large
    {"offset": 10000},  # Too large
]
