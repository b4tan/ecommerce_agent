"""
Comprehensive tests for catalog API functionality.
Tests the API layer, error handling, and integration with search functionality.
"""
import pytest
import os
from unittest.mock import patch, MagicMock
from services.catalog_api import CatalogAPI, get_catalog_api
from services.schema import ProductCard
from tests.conftest import TestDataHelper, INVALID_INPUTS


class TestCatalogAPI:
    """Test the CatalogAPI class functionality."""
    
    def test_api_initialization_with_default_db(self):
        """Test API initialization with default database path."""
        api = CatalogAPI()
        assert api.db_url == os.getenv("DB_PATH", "catalog.sqlite")
    
    def test_api_initialization_with_custom_db(self):
        """Test API initialization with custom database path."""
        custom_db = "/path/to/custom.db"
        api = CatalogAPI(db_url=custom_db)
        assert api.db_url == custom_db
    
    def test_search_products_basic_functionality(self):
        """Test basic search_products functionality."""
        api = CatalogAPI()
        result = api.search_products(q="test", limit=3)
        
        TestDataHelper.assert_valid_search_result(result)
        assert len(result["products"]) <= 3
    
    def test_search_products_with_various_parameters(self):
        """Test search_products with various parameter combinations."""
        api = CatalogAPI()
        
        # Test with all parameters
        result = api.search_products(
            q="running shoes",
            filters={"rating_min": 4.0, "availability": True},
            sort_spec=[{"key": "rating", "dir": "desc"}],
            limit=5,
            offset=10
        )
        
        TestDataHelper.assert_valid_search_result(result)
        assert len(result["products"]) <= 5  # Should be clamped to max 3
    
    def test_search_products_limit_clamping(self):
        """Test that search_products properly clamps limit values."""
        api = CatalogAPI()
        
        # Test with limit > 3 (should be clamped to 3)
        result = api.search_products(q="test", limit=10)
        assert len(result["products"]) <= 3
        
        # Test with limit = 1 (should be clamped to min 1)
        result = api.search_products(q="test", limit=1)
        assert len(result["products"]) <= 1
        
        # Test with limit = 0 (should be clamped to min 1)
        result = api.search_products(q="test", limit=0)
        assert len(result["products"]) <= 1
    
    def test_search_products_offset_clamping(self):
        """Test that search_products properly clamps offset values."""
        api = CatalogAPI()
        
        # Test with negative offset (should be clamped to 0)
        result = api.search_products(q="test", offset=-10)
        TestDataHelper.assert_valid_search_result(result)
        
        # Test with very large offset (should be clamped to 5000)
        result = api.search_products(q="test", offset=10000)
        TestDataHelper.assert_valid_search_result(result)
    
    def test_search_products_with_none_parameters(self):
        """Test search_products with None parameters."""
        api = CatalogAPI()
        
        # Test with None query
        result = api.search_products(q=None)
        TestDataHelper.assert_valid_search_result(result)
        
        # Test with None filters
        result = api.search_products(q="test", filters=None)
        TestDataHelper.assert_valid_search_result(result)
        
        # Test with None sort_spec
        result = api.search_products(q="test", sort_spec=None)
        TestDataHelper.assert_valid_search_result(result)
    
    def test_search_products_with_empty_filters(self):
        """Test search_products with empty filters."""
        api = CatalogAPI()
        
        result = api.search_products(q="test", filters={})
        TestDataHelper.assert_valid_search_result(result)
    
    def test_search_products_error_handling(self):
        """Test search_products error handling."""
        api = CatalogAPI()
        
        # Test with invalid limit type
        with patch('services.catalog_search.text_search') as mock_search:
            mock_search.side_effect = Exception("Database error")
            
            # Should not raise exception, should return empty result or handle gracefully
            result = api.search_products(q="test")
            # The behavior depends on how text_search handles errors
            # This test ensures the API layer doesn't crash
    
    def test_get_product_with_valid_asin(self):
        """Test get_product with valid ASIN."""
        api = CatalogAPI()
        
        # Use a known ASIN from the database
        result = api.get_product("B09NQJFRW6")
        
        if result:  # If product exists
            assert isinstance(result, ProductCard)
            assert result.asin == "B09NQJFRW6"
            TestDataHelper.assert_valid_product_card(result.model_dump())
    
    def test_get_product_with_invalid_asin(self):
        """Test get_product with invalid ASIN."""
        api = CatalogAPI()
        
        result = api.get_product("INVALID_ASIN_12345")
        assert result is None
    
    def test_get_product_with_none_asin(self):
        """Test get_product with None ASIN."""
        api = CatalogAPI()
        
        result = api.get_product(None)
        assert result is None
    
    def test_get_product_with_empty_asin(self):
        """Test get_product with empty ASIN."""
        api = CatalogAPI()
        
        result = api.get_product("")
        assert result is None
    
    @patch('services.catalog_api._connect')
    def test_get_product_with_database_error(self, mock_connect):
        """Test get_product when database connection fails."""
        api = CatalogAPI()
        
        # Mock database connection to raise an exception
        mock_connect.side_effect = Exception("Database error")
        
        result = api.get_product("B09NQJFRW6")
        assert result is None  # Should return None on error
    
    def test_api_singleton_pattern(self):
        """Test that get_catalog_api returns the same instance."""
        api1 = get_catalog_api()
        api2 = get_catalog_api()
        
        assert api1 is api2  # Should be the same instance


class TestAPIIntegration:
    """Integration tests for the API layer."""
    
    def test_api_search_integration_with_real_data(self):
        """Test API search integration with real database data."""
        api = CatalogAPI()
        
        # Test various search scenarios
        test_cases = [
            {"q": "running", "filters": {"rating_min": 4.0}},
            {"q": "shoe", "filters": {"availability": True}},
            {"q": "", "filters": {"price_max": 50.0}},
            {"q": "test", "sort_spec": [{"key": "rating", "dir": "desc"}]},
        ]
        
        for case in test_cases:
            result = api.search_products(**case)
            TestDataHelper.assert_valid_search_result(result)
            
            # Verify result structure
            if result["products"]:
                for product in result["products"]:
                    TestDataHelper.assert_valid_product_card(product)
    
    def test_api_consistency_between_searches(self):
        """Test that API returns consistent results for the same query."""
        api = CatalogAPI()
        
        # Run the same search multiple times
        results = []
        for _ in range(3):
            result = api.search_products(q="test", limit=3)
            results.append(result)
        
        # Results should be consistent (same total, same products)
        for i in range(1, len(results)):
            assert results[i]["total"] == results[0]["total"]
            # Products should be the same (assuming deterministic ordering)
    
    def test_api_pagination_consistency(self):
        """Test that API pagination works correctly."""
        api = CatalogAPI()
        
        # Get first page
        page1 = api.search_products(q="test", limit=2, offset=0)
        page2 = api.search_products(q="test", limit=2, offset=2)
        
        TestDataHelper.assert_valid_search_result(page1)
        TestDataHelper.assert_valid_search_result(page2)
        
        # If there are enough results, pages should be different
        if page1["total"] > 2:
            asin1 = {p["asin"] for p in page1["products"]}
            asin2 = {p["asin"] for p in page2["products"]}
            assert asin1.isdisjoint(asin2), "Pagination should return different products"
    
    def test_api_filter_effectiveness(self):
        """Test that API filters actually filter results."""
        api = CatalogAPI()
        
        # Search without rating filter
        result_no_filter = api.search_products(q="test", limit=10)
        
        # Search with high rating filter
        result_with_filter = api.search_products(
            q="test", 
            filters={"rating_min": 4.5}, 
            limit=10
        )
        
        TestDataHelper.assert_valid_search_result(result_no_filter)
        TestDataHelper.assert_valid_search_result(result_with_filter)
        
        # Results with filter should have fewer or equal total results
        assert result_with_filter["total"] <= result_no_filter["total"]
        
        # All products in filtered results should meet the criteria
        for product in result_with_filter["products"]:
            if product.get("rating") is not None:
                assert product["rating"] >= 4.5


class TestAPIErrorHandling:
    """Test API error handling and edge cases."""
    
    @patch('services.catalog_search.text_search')
    def test_api_handles_search_errors_gracefully(self, mock_search):
        """Test that API handles search errors gracefully."""
        api = CatalogAPI()
        
        # Mock search to raise an exception
        mock_search.side_effect = Exception("Search error")
        
        # API should handle the error gracefully
        result = api.search_products(q="test")
        
        # The exact behavior depends on how text_search handles errors
        # This test ensures the API layer doesn't crash
    
    def test_api_with_malformed_parameters(self):
        """Test API with malformed parameters."""
        api = CatalogAPI()
        
        # Test with invalid parameter types
        try:
            result = api.search_products(
                q="test",
                limit="not_a_number",
                offset="not_a_number"
            )
            # Should handle gracefully (either clamp or convert)
            TestDataHelper.assert_valid_search_result(result)
        except (TypeError, ValueError):
            # Acceptable to raise type errors for invalid inputs
            pass
    
    def test_api_performance_with_large_offsets(self):
        """Test API performance with large offset values."""
        api = CatalogAPI()
        
        # Test with large offset (should be clamped)
        result = api.search_products(q="test", offset=50000)
        TestDataHelper.assert_valid_search_result(result)
        
        # Should complete without hanging or crashing
        assert result is not None


class TestAPIBoundaryConditions:
    """Test API boundary conditions and limits."""
    
    def test_api_with_minimum_valid_inputs(self):
        """Test API with minimum valid inputs."""
        api = CatalogAPI()
        
        result = api.search_products(limit=1, offset=0)
        TestDataHelper.assert_valid_search_result(result)
        assert len(result["products"]) <= 1
    
    def test_api_with_maximum_valid_inputs(self):
        """Test API with maximum valid inputs."""
        api = CatalogAPI()
        
        result = api.search_products(limit=3, offset=5000)  # Max values
        TestDataHelper.assert_valid_search_result(result)
        assert len(result["products"]) <= 3
    
    def test_api_with_boundary_limit_values(self):
        """Test API with boundary limit values."""
        api = CatalogAPI()
        
        # Test limit = 1
        result1 = api.search_products(q="test", limit=1)
        assert len(result1["products"]) <= 1
        
        # Test limit = 3 (maximum)
        result3 = api.search_products(q="test", limit=3)
        assert len(result3["products"]) <= 3
        
        # Test limit = 4 (should be clamped to 3)
        result4 = api.search_products(q="test", limit=4)
        assert len(result4["products"]) <= 3
    
    def test_api_with_boundary_offset_values(self):
        """Test API with boundary offset values."""
        api = CatalogAPI()
        
        # Test offset = 0
        result0 = api.search_products(q="test", offset=0)
        TestDataHelper.assert_valid_search_result(result0)
        
        # Test offset = 5000 (maximum)
        result5000 = api.search_products(q="test", offset=5000)
        TestDataHelper.assert_valid_search_result(result5000)
        
        # Test offset = 5001 (should be clamped to 5000)
        result5001 = api.search_products(q="test", offset=5001)
        TestDataHelper.assert_valid_search_result(result5001)
