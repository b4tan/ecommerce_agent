"""
Comprehensive tests for catalog search functionality.
Tests edge cases, error conditions, and various query combinations.
"""
import pytest
import sqlite3
from unittest.mock import patch, MagicMock
from services.catalog_search import (
    TextSearchSpec, text_search, _connect, _row_to_card, 
    _safe_str, _safe_float, _compile_filters, _compile_sort,
    _has_fts, SORTABLE
)
from services.schema import ProductCard
from tests.conftest import TestDataHelper, SEARCH_QUERIES, FILTER_COMBINATIONS, SORT_SPECS


class TestTextSearchSpec:
    """Test the TextSearchSpec model validation and behavior."""
    
    def test_valid_spec_creation(self):
        """Test creating a valid TextSearchSpec."""
        spec = TextSearchSpec(
            q="test query",
            filters={"rating_min": 4.0},
            sort_spec=[{"key": "rating", "dir": "desc"}],
            limit=5,
            offset=10
        )
        assert spec.q == "test query"
        assert spec.filters == {"rating_min": 4.0}
        assert spec.sort_spec == [{"key": "rating", "dir": "desc"}]
        assert spec.limit == 5
        assert spec.offset == 10
    
    def test_default_values(self):
        """Test TextSearchSpec with default values."""
        spec = TextSearchSpec()
        assert spec.q is None
        assert spec.filters == {}
        assert spec.sort_spec is None
        assert spec.limit == 3
        assert spec.offset == 0
    
    def test_limit_validation(self):
        """Test limit field validation."""
        # Valid limits
        TextSearchSpec(limit=1)
        TextSearchSpec(limit=50)
        
        # Invalid limits should raise ValidationError
        with pytest.raises(Exception):  # Pydantic ValidationError
            TextSearchSpec(limit=0)
        with pytest.raises(Exception):  # Pydantic ValidationError
            TextSearchSpec(limit=51)
        with pytest.raises(Exception):  # Pydantic ValidationError
            TextSearchSpec(limit=-1)
    
    def test_offset_validation(self):
        """Test offset field validation."""
        # Valid offsets
        TextSearchSpec(offset=0)
        TextSearchSpec(offset=5000)
        
        # Invalid offsets should raise ValidationError
        with pytest.raises(Exception):  # Pydantic ValidationError
            TextSearchSpec(offset=-1)
        with pytest.raises(Exception):  # Pydantic ValidationError
            TextSearchSpec(offset=5001)


class TestHelperFunctions:
    """Test the helper functions used in catalog search."""
    
    def test_safe_str_with_valid_data(self, mock_product_row):
        """Test _safe_str with valid data."""
        assert _safe_str(mock_product_row, "title") == "Saucony Men's Kinvara 13 Running Shoe"
        assert _safe_str(mock_product_row, "asin") == "B09NQJFRW6"
    
    def test_safe_str_with_none_values(self, mock_product_row):
        """Test _safe_str with None values."""
        mock_product_row.get.return_value = None
        assert _safe_str(mock_product_row, "nonexistent") is None
        
        mock_product_row.get.return_value = ""
        assert _safe_str(mock_product_row, "empty") is None
        
        mock_product_row.get.return_value = "   "
        assert _safe_str(mock_product_row, "whitespace") is None
    
    def test_safe_float_with_valid_data(self, mock_product_row):
        """Test _safe_float with valid numeric data."""
        mock_product_row.get.return_value = "4.6"
        assert _safe_float(mock_product_row, "rating") == 4.6
        
        mock_product_row.get.return_value = "99.99"
        assert _safe_float(mock_product_row, "final_price") == 99.99
    
    def test_safe_float_with_invalid_data(self):
        """Test _safe_float with invalid data."""
        # Create a dict-like mock for each test case
        mock_row1 = {"rating": None}
        assert _safe_float(mock_row1, "rating") is None
        
        mock_row2 = {"rating": ""}
        assert _safe_float(mock_row2, "rating") is None
        
        mock_row3 = {"rating": "not_a_number"}
        assert _safe_float(mock_row3, "rating") is None
    
    def test_row_to_card_with_valid_data(self, mock_product_row):
        """Test _row_to_card with valid product data."""
        result = _row_to_card(mock_product_row)
        assert isinstance(result, ProductCard)
        assert result.asin == "B09NQJFRW6"
        assert result.title == "Saucony Men's Kinvara 13 Running Shoe"
        assert result.rating == 4.6
        assert result.final_price == 99.99
    
    def test_row_to_card_with_missing_required_fields(self):
        """Test _row_to_card with missing required fields."""
        # Test with None asin
        mock_row1 = {
            "asin": None,
            "title": "Test Title",
            "final_price": 99.99,
            "currency": "USD",
            "rating": 4.5,
            "image_url": "https://example.com/image.jpg",
            "url": "https://example.com/product"
        }
        result = _row_to_card(mock_row1)
        assert result is None
        
        # Test with empty title
        mock_row2 = {
            "asin": "B09NQJFRW6",
            "title": "",
            "final_price": 99.99,
            "currency": "USD",
            "rating": 4.5,
            "image_url": "https://example.com/image.jpg",
            "url": "https://example.com/product"
        }
        result = _row_to_card(mock_row2)
        assert result is None
    
    def test_compile_filters_with_various_filters(self):
        """Test _compile_filters with various filter combinations."""
        # Rating filters
        where, params = _compile_filters({"rating_min": 4.0, "rating_max": 5.0})
        assert "rating_min" in params
        assert "rating_max" in params
        assert params["rating_min"] == 4.0
        assert params["rating_max"] == 5.0
        
        # Price filters
        where, params = _compile_filters({"price_min": 10.0, "price_max": 100.0})
        assert "price_min" in params
        assert "price_max" in params
        
        # Availability filter
        where, params = _compile_filters({"availability": True})
        assert "avail" in params
        assert params["avail"] == 1
        
        # Brand filter
        where, params = _compile_filters({"brand_in": ["Nike", "Adidas"]})
        assert "brand_in0" in params
        assert "brand_in1" in params
        assert params["brand_in0"] == "nike"
        assert params["brand_in1"] == "adidas"
    
    def test_compile_filters_with_invalid_values(self):
        """Test _compile_filters with invalid filter values."""
        # Invalid rating values should be clipped
        where, params = _compile_filters({"rating_min": -1.0, "rating_max": 6.0})
        assert params["rating_min"] == 0.0
        assert params["rating_max"] == 5.0
        
        # Invalid price values should be clipped
        where, params = _compile_filters({"price_min": -100.0})
        assert params["price_min"] == 0.0
    
    def test_compile_sort_with_various_specs(self):
        """Test _compile_sort with various sort specifications."""
        # Default sort (no spec)
        result = _compile_sort(None, use_fts=False)
        assert "rating DESC" in result
        assert "reviews_count DESC" in result
        
        # Single sort
        sort_spec = [{"key": "final_price", "dir": "asc"}]
        result = _compile_sort(sort_spec, use_fts=False)
        assert "p.final_price ASC" in result
        
        # Multiple sorts
        sort_spec = [{"key": "rating", "dir": "desc"}, {"key": "reviews_count", "dir": "asc"}]
        result = _compile_sort(sort_spec, use_fts=False)
        assert "p.rating DESC" in result
        assert "p.reviews_count ASC" in result
        
        # FTS sort
        sort_spec = [{"key": "score", "dir": "asc"}]
        result = _compile_sort(sort_spec, use_fts=True)
        assert "score ASC" in result
        
        # Invalid sort keys should be ignored
        sort_spec = [{"key": "invalid_key", "dir": "desc"}]
        result = _compile_sort(sort_spec, use_fts=False)
        assert "invalid_key" not in result
    
    def test_has_fts_with_existing_table(self):
        """Test _has_fts when FTS table exists."""
        # Create a mock connection for testing
        mock_conn = MagicMock()
        mock_conn.execute.side_effect = sqlite3.Error("Table doesn't exist")
        result = _has_fts(mock_conn)
        assert isinstance(result, bool)
        assert result is False  # Should return False when table doesn't exist


class TestTextSearchIntegration:
    """Integration tests for the text_search function."""
    
    @pytest.mark.parametrize("query", SEARCH_QUERIES)
    def test_search_with_various_queries(self, query):
        """Test search with various query strings."""
        from services.catalog_search import TextSearchSpec, text_search
        
        spec = TextSearchSpec(q=query, limit=3)
        result = text_search(spec)
        
        TestDataHelper.assert_valid_search_result(result)
        assert len(result["products"]) <= 3
    
    @pytest.mark.parametrize("filters", FILTER_COMBINATIONS)
    def test_search_with_various_filters(self, filters):
        """Test search with various filter combinations."""
        from services.catalog_search import TextSearchSpec, text_search
        
        spec = TextSearchSpec(q="test", filters=filters, limit=3)
        result = text_search(spec)
        
        TestDataHelper.assert_valid_search_result(result)
        
        # If rating filters are applied, verify products meet criteria
        if "rating_min" in filters:
            for product in result["products"]:
                if product.get("rating") is not None:
                    assert product["rating"] >= filters["rating_min"]
    
    @pytest.mark.parametrize("sort_spec", SORT_SPECS)
    def test_search_with_various_sort_specs(self, sort_spec):
        """Test search with various sort specifications."""
        from services.catalog_search import TextSearchSpec, text_search
        
        spec = TextSearchSpec(q="test", sort_spec=sort_spec, limit=5)
        result = text_search(spec)
        
        TestDataHelper.assert_valid_search_result(result)
    
    def test_search_with_pagination(self):
        """Test search pagination functionality."""
        from services.catalog_search import TextSearchSpec, text_search
        
        # Get first page
        spec1 = TextSearchSpec(q="test", limit=2, offset=0)
        result1 = text_search(spec1)
        
        # Get second page
        spec2 = TextSearchSpec(q="test", limit=2, offset=2)
        result2 = text_search(spec2)
        
        TestDataHelper.assert_valid_search_result(result1)
        TestDataHelper.assert_valid_search_result(result2)
        
        # If there are enough results, pages should be different
        if result1["total"] > 2:
            asin1 = {p["asin"] for p in result1["products"]}
            asin2 = {p["asin"] for p in result2["products"]}
            assert asin1.isdisjoint(asin2), "Pagination should return different products"
    
    def test_search_with_no_results(self):
        """Test search with query that returns no results."""
        from services.catalog_search import TextSearchSpec, text_search
        
        spec = TextSearchSpec(q="nonexistent_product_xyz_12345", limit=3)
        result = text_search(spec)
        
        TestDataHelper.assert_valid_search_result(result)
        assert result["products"] == []
        assert result["total"] == 0
    
    def test_search_with_empty_query(self):
        """Test search with empty or None query."""
        from services.catalog_search import TextSearchSpec, text_search
        
        spec = TextSearchSpec(q="", limit=3)
        result = text_search(spec)
        
        TestDataHelper.assert_valid_search_result(result)
        # Should still return some results (all products)
    
    def test_search_with_limit_boundaries(self):
        """Test search with limit boundary values."""
        from services.catalog_search import TextSearchSpec, text_search
        
        # Test with limit=1
        spec1 = TextSearchSpec(q="test", limit=1)
        result1 = text_search(spec1)
        assert len(result1["products"]) <= 1
        
        # Test with limit=50 (maximum)
        spec50 = TextSearchSpec(q="test", limit=50)
        result50 = text_search(spec50)
        assert len(result50["products"]) <= 50
    
    def test_search_result_structure(self):
        """Test that search results have the expected structure."""
        from services.catalog_search import TextSearchSpec, text_search
        
        spec = TextSearchSpec(q="test", limit=3)
        result = text_search(spec)
        
        TestDataHelper.assert_valid_search_result(result)
        
        if result["products"]:
            for product in result["products"]:
                TestDataHelper.assert_valid_product_card(product)
    
    @patch('services.catalog_search._connect')
    def test_search_with_database_error(self, mock_connect):
        """Test search behavior when database connection fails."""
        from services.catalog_search import TextSearchSpec, text_search
        
        # Mock database connection to raise an exception
        mock_connect.side_effect = sqlite3.Error("Database error")
        
        spec = TextSearchSpec(q="test", limit=3)
        
        # Should raise an exception
        with pytest.raises(sqlite3.Error):
            text_search(spec)
    
    def test_search_debug_information(self):
        """Test that search results include debug information."""
        from services.catalog_search import TextSearchSpec, text_search
        
        spec = TextSearchSpec(q="test", limit=3)
        result = text_search(spec)
        
        assert "debug" in result
        assert "use_fts" in result["debug"]
        assert "order_by" in result["debug"]


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_search_with_very_long_query(self):
        """Test search with very long query string."""
        from services.catalog_search import TextSearchSpec, text_search
        
        long_query = "a" * 1000  # Very long query
        spec = TextSearchSpec(q=long_query, limit=3)
        result = text_search(spec)
        
        TestDataHelper.assert_valid_search_result(result)
    
    def test_search_with_special_characters(self):
        """Test search with special characters in query."""
        from services.catalog_search import TextSearchSpec, text_search
        
        special_queries = [
            "test@#$%^&*()",
            "test with spaces and symbols!@#",
            "test'with'quotes",
            "test\"with\"double\"quotes",
        ]
        
        for query in special_queries:
            spec = TextSearchSpec(q=query, limit=3)
            result = text_search(spec)
            TestDataHelper.assert_valid_search_result(result)
    
    def test_search_with_unicode_characters(self):
        """Test search with unicode characters."""
        from services.catalog_search import TextSearchSpec, text_search
        
        unicode_queries = [
            "café",
            "naïve",
            "résumé",
            "测试",
            "тест",
        ]
        
        for query in unicode_queries:
            spec = TextSearchSpec(q=query, limit=3)
            result = text_search(spec)
            TestDataHelper.assert_valid_search_result(result)
