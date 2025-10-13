"""
Comprehensive tests for the product_search tool functionality.
Tests input validation, error handling, output formatting, and integration.
"""
import pytest
from unittest.mock import patch, MagicMock
from backend.agent.tools import product_search
from services.catalog_search import TextSearchSpec
from tests.conftest import TestDataHelper, INVALID_INPUTS


class TestProductSearchTool:
    """Test the product_search tool functionality."""
    
    def test_tool_basic_functionality(self):
        """Test basic tool functionality with valid input."""
        payload = TestDataHelper.create_valid_payload()
        result = product_search.invoke(payload)
        
        TestDataHelper.assert_valid_search_result(result)
    
    def test_tool_with_various_queries(self):
        """Test tool with various query strings."""
        test_queries = [
            "running shoes",
            "laptop computer",
            "wireless headphones",
            "",  # Empty query
            "nonexistent_product_xyz",  # No results expected
        ]
        
        for query in test_queries:
            payload = TestDataHelper.create_valid_payload(q=query)
            result = product_search.invoke(payload)
            
            TestDataHelper.assert_valid_search_result(result)
    
    def test_tool_with_various_filters(self):
        """Test tool with various filter combinations."""
        filter_combinations = [
            {},
            {"rating_min": 4.0},
            {"rating_min": 3.0, "rating_max": 5.0},
            {"price_min": 10.0, "price_max": 100.0},
            {"availability": True},
            {"brand_in": ["Nike", "Adidas"]},
            {"rating_min": 4.0, "availability": True, "price_max": 50.0},
        ]
        
        for filters in filter_combinations:
            payload = TestDataHelper.create_valid_payload(filters=filters)
            result = product_search.invoke(payload)
            
            TestDataHelper.assert_valid_search_result(result)
    
    def test_tool_with_various_sort_specs(self):
        """Test tool with various sort specifications."""
        sort_specs = [
            None,
            [{"key": "rating", "dir": "desc"}],
            [{"key": "final_price", "dir": "asc"}],
            [{"key": "reviews_count", "dir": "desc"}],
            [{"key": "rating", "dir": "desc"}, {"key": "reviews_count", "dir": "desc"}],
        ]
        
        for sort_spec in sort_specs:
            payload = TestDataHelper.create_valid_payload(sort_spec=sort_spec)
            result = product_search.invoke(payload)
            
            TestDataHelper.assert_valid_search_result(result)
    
    def test_tool_limit_clamping(self):
        """Test that tool properly clamps limit values."""
        # Test with limit > 3 (should be clamped to 3)
        payload = TestDataHelper.create_valid_payload(limit=10)
        result = product_search.invoke(payload)
        TestDataHelper.assert_valid_search_result(result)
        assert len(result["products"]) <= 3
        
        # Test with limit = 1 (should be clamped to min 1)
        payload = TestDataHelper.create_valid_payload(limit=1)
        result = product_search.invoke(payload)
        TestDataHelper.assert_valid_search_result(result)
        assert len(result["products"]) <= 1
        
        # Test with limit = 0 (should be clamped to min 1)
        payload = TestDataHelper.create_valid_payload(limit=0)
        result = product_search.invoke(payload)
        TestDataHelper.assert_valid_search_result(result)
        assert len(result["products"]) <= 1
    
    def test_tool_with_pagination(self):
        """Test tool pagination functionality."""
        # Get first page
        payload1 = TestDataHelper.create_valid_payload(limit=2, offset=0)
        result1 = product_search.invoke(payload1)
        
        # Get second page
        payload2 = TestDataHelper.create_valid_payload(limit=2, offset=2)
        result2 = product_search.invoke(payload2)
        
        TestDataHelper.assert_valid_search_result(result1)
        TestDataHelper.assert_valid_search_result(result2)
        
        # If there are enough results, pages should be different
        if result1["total"] > 2:
            asin1 = {p["asin"] for p in result1["products"]}
            asin2 = {p["asin"] for p in result2["products"]}
            assert asin1.isdisjoint(asin2), "Pagination should return different products"
    
    def test_tool_result_structure(self):
        """Test that tool results have the expected structure."""
        payload = TestDataHelper.create_valid_payload()
        result = product_search.invoke(payload)
        
        TestDataHelper.assert_valid_search_result(result)
        
        if result["products"]:
            for product in result["products"]:
                TestDataHelper.assert_valid_product_card(product)


class TestToolInputValidation:
    """Test tool input validation and error handling."""
    
    def test_tool_with_none_payload(self):
        """Test tool with None payload."""
        with pytest.raises(Exception):  # Should raise ValidationError
            product_search.invoke(None)
    
    def test_tool_with_empty_payload(self):
        """Test tool with empty payload."""
        with pytest.raises(Exception):  # Should raise ValidationError
            product_search.invoke({})
    
    def test_tool_with_missing_payload_key(self):
        """Test tool with missing 'payload' key."""
        with pytest.raises(Exception):  # Should raise ValidationError
            product_search.invoke({"invalid_key": "value"})
    
    def test_tool_with_invalid_payload_structure(self):
        """Test tool with invalid payload structure."""
        invalid_payloads = [
            {"payload": "not_a_dict"},
            {"payload": None},
            {"payload": []},
        ]
        
        for invalid_payload in invalid_payloads:
            with pytest.raises(Exception):  # Should raise ValidationError
                product_search.invoke(invalid_payload)
    
    def test_tool_with_invalid_parameter_types(self):
        """Test tool with invalid parameter types."""
        invalid_payloads = [
            TestDataHelper.create_valid_payload(limit="not_a_number"),
            TestDataHelper.create_valid_payload(offset="not_a_number"),
            TestDataHelper.create_valid_payload(filters="not_a_dict"),
            TestDataHelper.create_valid_payload(sort_spec="not_a_list"),
        ]
        
        for invalid_payload in invalid_payloads:
            result = product_search.invoke(invalid_payload)
            
            # Should handle gracefully
            TestDataHelper.assert_valid_search_result(result)
    
    def test_tool_with_extreme_values(self):
        """Test tool with extreme parameter values."""
        # Test with very large limit (should be clamped)
        payload = TestDataHelper.create_valid_payload(limit=1000000)
        result = product_search.invoke(payload)
        TestDataHelper.assert_valid_search_result(result)
        assert len(result["products"]) <= 3
        
        # Test with very large offset (should be clamped)
        payload = TestDataHelper.create_valid_payload(offset=1000000)
        result = product_search.invoke(payload)
        TestDataHelper.assert_valid_search_result(result)
        
        # Test with negative limit (should be clamped)
        payload = TestDataHelper.create_valid_payload(limit=-100)
        result = product_search.invoke(payload)
        TestDataHelper.assert_valid_search_result(result)
        assert len(result["products"]) <= 1
        
        # Test with negative offset (should be clamped)
        payload = TestDataHelper.create_valid_payload(offset=-100)
        result = product_search.invoke(payload)
        TestDataHelper.assert_valid_search_result(result)
    
    def test_tool_with_malformed_sort_spec(self):
        """Test tool with malformed sort specifications."""
        malformed_sort_specs = [
            [{"invalid_key": "value"}],
            [{"key": "rating"}],  # Missing dir
            [{"dir": "desc"}],    # Missing key
            [{"key": "invalid_field", "dir": "desc"}],
            [{"key": "rating", "dir": "invalid_direction"}],
        ]
        
        for sort_spec in malformed_sort_specs:
            payload = TestDataHelper.create_valid_payload(sort_spec=sort_spec)
            result = product_search.invoke(payload)
            
            # Should handle gracefully
            TestDataHelper.assert_valid_search_result(result)


class TestToolErrorHandling:
    """Test tool error handling and edge cases."""
    
    @patch('backend.agent.tools.text_search')
    def test_tool_handles_search_errors(self, mock_search):
        """Test that tool handles search errors gracefully."""
        # Mock search to raise an exception
        mock_search.side_effect = Exception("Search error")
        
        payload = TestDataHelper.create_valid_payload()
        result = product_search.invoke(payload)
        
        # Should return error information in debug field
        assert "debug" in result
        assert "error" in result["debug"]
        assert result["products"] == []
        assert result["total"] == 0
    
    @patch('backend.agent.tools.TextSearchSpec')
    def test_tool_handles_spec_creation_errors(self, mock_spec):
        """Test that tool handles TextSearchSpec creation errors."""
        # Mock TextSearchSpec to raise an exception
        mock_spec.side_effect = Exception("Spec creation error")
        
        payload = TestDataHelper.create_valid_payload()
        result = product_search.invoke(payload)
        
        # Should return error information in debug field
        assert "debug" in result
        assert "error" in result["debug"]
        assert result["products"] == []
        assert result["total"] == 0
    
    def test_tool_with_very_long_query(self):
        """Test tool with very long query string."""
        long_query = "a" * 10000  # Very long query
        payload = TestDataHelper.create_valid_payload(q=long_query)
        result = product_search.invoke(payload)
        
        TestDataHelper.assert_valid_search_result(result)
    
    def test_tool_with_special_characters_in_query(self):
        """Test tool with special characters in query."""
        special_queries = [
            "test@#$%^&*()",
            "test with spaces and symbols!@#",
            "test'with'quotes",
            "test\"with\"double\"quotes",
            "test\nwith\nnewlines",
            "test\twith\ttabs",
        ]
        
        for query in special_queries:
            payload = TestDataHelper.create_valid_payload(q=query)
            result = product_search.invoke(payload)
            
            TestDataHelper.assert_valid_search_result(result)
    
    def test_tool_with_unicode_characters(self):
        """Test tool with unicode characters."""
        unicode_queries = [
            "café",
            "naïve",
            "résumé",
            "测试",
            "тест",
            "🎵🎶",
        ]
        
        for query in unicode_queries:
            payload = TestDataHelper.create_valid_payload(q=query)
            result = product_search.invoke(payload)
            
            TestDataHelper.assert_valid_search_result(result)


class TestToolIntegration:
    """Integration tests for the tool."""
    
    def test_tool_consistency_between_calls(self):
        """Test that tool returns consistent results for the same input."""
        payload = TestDataHelper.create_valid_payload()
        
        # Call tool multiple times with same input
        results = []
        for _ in range(3):
            result = product_search.invoke(payload)
            results.append(result)
        
        # Results should be consistent
        for i in range(1, len(results)):
            assert results[i]["total"] == results[0]["total"]
    
    def test_tool_performance_with_complex_queries(self):
        """Test tool performance with complex queries."""
        complex_payloads = [
            TestDataHelper.create_valid_payload(
                q="running shoes",
                filters={"rating_min": 4.0, "price_max": 100.0, "availability": True},
                sort_spec=[{"key": "rating", "dir": "desc"}, {"key": "reviews_count", "dir": "desc"}],
                limit=3,
                offset=0
            ),
            TestDataHelper.create_valid_payload(
                q="laptop computer",
                filters={"brand_in": ["Apple", "Dell", "HP"], "rating_min": 3.5},
                sort_spec=[{"key": "final_price", "dir": "asc"}],
                limit=3,
                offset=10
            ),
        ]
        
        for payload in complex_payloads:
            result = product_search.invoke(payload)
            TestDataHelper.assert_valid_search_result(result)
            
            # Should complete in reasonable time (no timeout)
            assert result is not None
    
    def test_tool_memory_usage(self):
        """Test tool memory usage with large result sets."""
        # Test with maximum allowed limit
        payload = TestDataHelper.create_valid_payload(limit=3)
        result = product_search.invoke(payload)
        
        TestDataHelper.assert_valid_search_result(result)
        
        # Result should not be excessively large
        import sys
        result_size = sys.getsizeof(result)
        assert result_size < 1024 * 1024  # Less than 1MB
    
    def test_tool_concurrent_calls(self):
        """Test tool behavior with concurrent calls."""
        import threading
        import time
        
        results = []
        errors = []
        
        def call_tool():
            try:
                payload = TestDataHelper.create_valid_payload()
                result = product_search.invoke(payload)
                results.append(result)
            except Exception as e:
                errors.append(e)
        
        # Create multiple threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=call_tool)
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # All calls should succeed
        assert len(errors) == 0
        assert len(results) == 5
        
        # All results should be valid
        for result in results:
            TestDataHelper.assert_valid_search_result(result)
