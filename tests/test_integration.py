"""
Integration tests that test the complete flow from tool to database.
These tests ensure the entire system works together correctly.
"""
import pytest
from backend.agent.tools import product_search
from services.catalog_api import get_catalog_api
from services.catalog_search import TextSearchSpec, text_search
from tests.conftest import TestDataHelper


class TestEndToEndIntegration:
    """Test complete end-to-end functionality."""
    
    def test_tool_to_database_integration(self):
        """Test complete flow from tool call to database results."""
        # Use the tool
        payload = TestDataHelper.create_valid_payload(
            q="running shoes",
            filters={"rating_min": 4.0},
            sort_spec=[{"key": "rating", "dir": "desc"}],
            limit=3
        )
        
        tool_result = product_search.invoke(payload)
        TestDataHelper.assert_valid_search_result(tool_result)
        
        # Use the API directly with same parameters
        api = get_catalog_api()
        api_result = api.search_products(
            q="running shoes",
            filters={"rating_min": 4.0},
            sort_spec=[{"key": "rating", "dir": "desc"}],
            limit=3
        )
        TestDataHelper.assert_valid_search_result(api_result)
        
        # Use the search function directly
        spec = TextSearchSpec(
            q="running shoes",
            filters={"rating_min": 4.0},
            sort_spec=[{"key": "rating", "dir": "desc"}],
            limit=3
        )
        search_result = text_search(spec)
        TestDataHelper.assert_valid_search_result(search_result)
        
        # All three should return the same results (or at least consistent structure)
        assert tool_result["total"] == api_result["total"]
        assert api_result["total"] == search_result["total"]
        
        # All should have the same number of products
        assert len(tool_result["products"]) == len(api_result["products"])
        assert len(api_result["products"]) == len(search_result["products"])
    
    def test_real_world_search_scenarios(self):
        """Test realistic search scenarios an agent might encounter."""
        scenarios = [
            {
                "name": "High-rated running shoes",
                "payload": TestDataHelper.create_valid_payload(
                    q="running shoes",
                    filters={"rating_min": 4.5, "availability": True},
                    sort_spec=[{"key": "rating", "dir": "desc"}],
                    limit=3
                )
            },
            {
                "name": "Budget electronics under $50",
                "payload": TestDataHelper.create_valid_payload(
                    q="electronics",
                    filters={"price_max": 50.0, "availability": True},
                    sort_spec=[{"key": "final_price", "dir": "asc"}],
                    limit=3
                )
            },
            {
                "name": "Popular items with many reviews",
                "payload": TestDataHelper.create_valid_payload(
                    q="laptop",
                    filters={"reviews_min": 100},
                    sort_spec=[{"key": "reviews_count", "dir": "desc"}],
                    limit=3
                )
            },
            {
                "name": "Brand-specific search",
                "payload": TestDataHelper.create_valid_payload(
                    q="headphones",
                    filters={"brand_in": ["Sony", "Bose"], "rating_min": 4.0},
                    sort_spec=[{"key": "rating", "dir": "desc"}],
                    limit=3
                )
            },
            {
                "name": "No filters, just query",
                "payload": TestDataHelper.create_valid_payload(
                    q="book",
                    filters={},
                    sort_spec=None,
                    limit=3
                )
            }
        ]
        
        for scenario in scenarios:
            result = product_search.invoke(scenario["payload"])
            
            TestDataHelper.assert_valid_search_result(result)
            
            # Each scenario should return results or at least handle gracefully
            assert isinstance(result, dict)
            assert "products" in result
            assert "total" in result
            
            # If there are products, they should be valid
            if result["products"]:
                for product in result["products"]:
                    TestDataHelper.assert_valid_product_card(product)
    
    def test_error_propagation_consistency(self):
        """Test that errors are handled consistently across all layers."""
        # Test with invalid input that should cause errors
        invalid_payload = {"invalid": "data"}
        
        # Tool should raise ValidationError for invalid input
        with pytest.raises(Exception):  # ValidationError
            product_search.invoke(invalid_payload)
    
    def test_performance_under_load(self):
        """Test system performance under simulated load."""
        import time
        
        # Simulate multiple concurrent-like searches
        queries = ["shoes", "laptop", "phone", "book", "watch", "camera"]
        start_time = time.time()
        
        results = []
        for query in queries:
            payload = TestDataHelper.create_valid_payload(q=query)
            result = product_search.invoke(payload)
            results.append(result)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # All searches should complete in reasonable time
        assert total_time < 10.0, f"All searches took too long: {total_time:.2f}s"
        
        # All results should be valid
        for result in results:
            TestDataHelper.assert_valid_search_result(result)
    
    def test_data_consistency_across_layers(self):
        """Test that data is consistent across all system layers."""
        # Use the same search parameters across all layers
        query = "test"
        filters = {"rating_min": 3.0}
        sort_spec = [{"key": "rating", "dir": "desc"}]
        limit = 3
        
        # Tool layer
        tool_payload = TestDataHelper.create_valid_payload(
            q=query, filters=filters, sort_spec=sort_spec, limit=limit
        )
        tool_result = product_search.invoke(tool_payload)
        
        # API layer
        api = get_catalog_api()
        api_result = api.search_products(
            q=query, filters=filters, sort_spec=sort_spec, limit=limit
        )
        
        # Search layer
        spec = TextSearchSpec(
            q=query, filters=filters, sort_spec=sort_spec, limit=limit
        )
        search_result = text_search(spec)
        
        # Results should be consistent
        assert tool_result["total"] == api_result["total"]
        assert api_result["total"] == search_result["total"]
        
        # Product structures should be the same
        if tool_result["products"] and api_result["products"]:
            tool_product = tool_result["products"][0]
            api_product = api_result["products"][0]
            
            # Should have same keys
            assert set(tool_product.keys()) == set(api_product.keys())
            
            # Required fields should match
            assert tool_product["asin"] == api_product["asin"]
            assert tool_product["title"] == api_product["title"]


class TestSystemReliability:
    """Test system reliability and robustness."""
    
    def test_system_handles_empty_database(self):
        """Test system behavior with empty database (if possible)."""
        # This test would require temporarily emptying the database
        # For now, test with a query that returns no results
        payload = TestDataHelper.create_valid_payload(q="nonexistent_product_xyz_12345")
        result = product_search.invoke(payload)
        
        TestDataHelper.assert_valid_search_result(result)
        assert result["products"] == []
        assert result["total"] == 0
    
    def test_system_handles_corrupted_data(self):
        """Test system behavior with potentially corrupted data."""
        # Test with queries that might hit edge cases in data
        edge_case_queries = [
            "",  # Empty query
            "   ",  # Whitespace only
            "a" * 1000,  # Very long query
            "!@#$%^&*()",  # Special characters
        ]
        
        for query in edge_case_queries:
            payload = TestDataHelper.create_valid_payload(q=query)
            result = product_search.invoke(payload)
            
            TestDataHelper.assert_valid_search_result(result)
            # System should not crash
    
    def test_system_memory_usage(self):
        """Test system memory usage with large result sets."""
        # Test with maximum allowed limit
        payload = TestDataHelper.create_valid_payload(limit=3)
        result = product_search.invoke(payload)
        
        TestDataHelper.assert_valid_search_result(result)
        
        # Result should not be excessively large
        import sys
        result_size = sys.getsizeof(result)
        assert result_size < 1024 * 1024  # Less than 1MB
    
    def test_system_concurrent_access(self):
        """Test system behavior under concurrent access."""
        import threading
        import time
        
        results = []
        errors = []
        
        def search_worker(worker_id):
            try:
                payload = TestDataHelper.create_valid_payload(q=f"test_{worker_id}")
                result = product_search.invoke(payload)
                results.append((worker_id, result))
            except Exception as e:
                errors.append((worker_id, e))
        
        # Create multiple threads
        threads = []
        for i in range(10):
            thread = threading.Thread(target=search_worker, args=(i,))
            threads.append(thread)
        
        # Start all threads
        start_time = time.time()
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # All searches should complete
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 10, "Not all searches completed"
        
        # Should complete in reasonable time
        assert total_time < 30.0, f"Concurrent searches took too long: {total_time:.2f}s"
        
        # All results should be valid
        for worker_id, result in results:
            TestDataHelper.assert_valid_search_result(result)
