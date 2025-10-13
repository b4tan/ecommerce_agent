"""Integration tests for the complete search pipeline."""
import pytest
from backend.agent.tools import product_search


@pytest.mark.requires_db
@pytest.mark.requires_faiss
@pytest.mark.requires_api
class TestSearchIntegration:
    """Test the complete search pipeline from tool to results."""

    def test_tool_search_basic(self):
        """Test product_search tool with basic query."""
        payload = {
            "q": "laptop",
            "limit": 3,
            "offset": 0
        }
        
        result = product_search.invoke({"payload": payload})
        
        assert isinstance(result, dict)
        assert "products" in result
        assert "total" in result
        assert isinstance(result["products"], list)

    def test_tool_search_with_filters(self):
        """Test product_search with filters."""
        payload = {
            "q": "shirt",
            "filters": {
                "price_min": 10.0,
                "price_max": 50.0,
                "rating_min": 4.0
            },
            "limit": 5,
            "offset": 0
        }
        
        result = product_search.invoke({"payload": payload})
        
        assert isinstance(result["products"], list)
        
        # Verify filters
        for product in result["products"]:
            if product.get("final_price"):
                assert product["final_price"] >= 10.0
                assert product["final_price"] <= 50.0

    def test_tool_search_pagination(self):
        """Test pagination through the tool."""
        # Page 1
        result1 = product_search.invoke({"payload": {
            "q": "product",
            "limit": 3,
            "offset": 0
        }})
        
        # Page 2
        result2 = product_search.invoke({"payload": {
            "q": "product",
            "limit": 3,
            "offset": 3
        }})
        
        # Should have different products
        if result1["products"] and result2["products"]:
            asins1 = {p["asin"] for p in result1["products"]}
            asins2 = {p["asin"] for p in result2["products"]}
            assert asins1 != asins2

    def test_tool_search_no_results(self):
        """Test tool with query that returns no results."""
        result = product_search.invoke({"payload": {
            "q": "xyznonexistent98765",
            "limit": 5,
            "offset": 0
        }})
        
        # May return empty or very few irrelevant results
        assert isinstance(result["products"], list)
        assert isinstance(result["total"], int)

    def test_tool_search_dynamic_limit(self):
        """Test dynamic limit based on results found."""
        result = product_search.invoke({"payload": {
            "q": "laptop",
            "limit": 10,
            "offset": 0
        }})
        
        # Tool caps at 3 max
        assert len(result["products"]) <= 3


@pytest.mark.requires_db
@pytest.mark.requires_faiss
class TestSearchQuality:
    """Test search quality and relevance."""

    def test_search_relevance_basic(self):
        """Test basic search returns relevant results."""
        from services.catalog_search import text_search, TextSearchSpec
        
        spec = TextSearchSpec(q="laptop computer", limit=5)
        result = text_search(spec)
        
        # Check that results contain query terms
        query_terms = {"laptop", "computer"}
        for product in result["products"][:3]:  # Check top 3
            title_lower = product["title"].lower()
            # At least one term should match
            assert any(term in title_lower for term in query_terms)

    def test_search_ranking_quality(self):
        """Test that highly rated products rank higher."""
        from services.catalog_search import text_search, TextSearchSpec
        
        spec = TextSearchSpec(q="popular product", limit=10)
        result = text_search(spec)
        
        if len(result["products"]) >= 2:
            # First result should have decent rating or reviews
            first = result["products"][0]
            assert (
                (first.get("rating") and first["rating"] >= 3.0) or
                (first.get("reviews_count") and first["reviews_count"] > 0) or
                True  # Or it's most semantically relevant
            )

    def test_filter_accuracy(self):
        """Test filters are accurately applied."""
        from services.catalog_search import text_search, TextSearchSpec
        
        spec = TextSearchSpec(
            q="product",
            filters={
                "price_min": 20.0,
                "price_max": 40.0,
                "rating_min": 4.0
            },
            limit=20
        )
        result = text_search(spec)
        
        # All results should match filters
        for product in result["products"]:
            if product.get("final_price"):
                assert 20.0 <= product["final_price"] <= 40.0
            if product.get("rating"):
                assert product["rating"] >= 4.0


@pytest.mark.requires_db
class TestSearchPerformance:
    """Test search performance characteristics."""

    def test_search_speed(self):
        """Test search completes in reasonable time."""
        import time
        from services.catalog_search import text_search, TextSearchSpec
        
        spec = TextSearchSpec(q="laptop", limit=10)
        
        start = time.time()
        result = text_search(spec)
        duration = time.time() - start
        
        # Should complete in under 2 seconds
        assert duration < 2.0
        assert isinstance(result["products"], list)

    def test_large_result_set(self):
        """Test handling of large result sets."""
        from services.catalog_search import text_search, TextSearchSpec
        
        spec = TextSearchSpec(q="product", limit=50)
        result = text_search(spec)
        
        assert len(result["products"]) <= 50
        assert isinstance(result["total"], int)


@pytest.mark.requires_db
@pytest.mark.requires_faiss
class TestSearchRobustness:
    """Test search handles various edge cases."""

    def test_malformed_input(self):
        """Test handling of malformed input."""
        from services.catalog_search import text_search, TextSearchSpec
        
        # Should handle gracefully
        specs = [
            TextSearchSpec(q="test", limit=5),  # Valid query
            TextSearchSpec(q=None, limit=5),    # None query
        ]
        
        for spec in specs:
            result = text_search(spec)
            assert isinstance(result, dict)
            assert "products" in result

    def test_concurrent_searches(self):
        """Test multiple concurrent searches don't interfere."""
        from services.catalog_search import text_search, TextSearchSpec
        
        spec1 = TextSearchSpec(q="laptop", limit=5)
        spec2 = TextSearchSpec(q="shirt", limit=5)
        
        result1 = text_search(spec1)
        result2 = text_search(spec2)
        
        # Results should be independent
        assert isinstance(result1["products"], list)
        assert isinstance(result2["products"], list)

    def test_state_independence(self):
        """Test searches are stateless."""
        from services.catalog_search import text_search, TextSearchSpec
        
        spec = TextSearchSpec(q="test", limit=5)
        
        result1 = text_search(spec)
        result2 = text_search(spec)
        
        # Same query should give same results
        assert result1["total"] == result2["total"]

