"""Tests for catalog_search.py"""
import pytest
from services.catalog_search import text_search, TextSearchSpec, _row_to_card


@pytest.mark.requires_db
@pytest.mark.requires_faiss
class TestCatalogSearch:
    """Test catalog search API."""

    def test_text_search_basic(self):
        """Test basic text search."""
        spec = TextSearchSpec(q="laptop", limit=5)
        result = text_search(spec)
        
        assert "products" in result
        assert "total" in result
        assert "debug" in result
        assert isinstance(result["products"], list)
        assert isinstance(result["total"], int)

    def test_text_search_with_filters(self):
        """Test search with filters."""
        spec = TextSearchSpec(
            q="shirt",
            filters={
                "price_min": 10.0,
                "price_max": 100.0,
                "rating_min": 4.0
            },
            limit=10
        )
        result = text_search(spec)
        
        assert isinstance(result["products"], list)
        
        # Verify filters applied
        for product in result["products"]:
            if product.get("final_price"):
                assert product["final_price"] >= 10.0
                assert product["final_price"] <= 100.0
            if product.get("rating"):
                assert product["rating"] >= 4.0

    def test_text_search_pagination(self):
        """Test pagination."""
        spec1 = TextSearchSpec(q="product", limit=5, offset=0)
        result1 = text_search(spec1)
        
        spec2 = TextSearchSpec(q="product", limit=5, offset=5)
        result2 = text_search(spec2)
        
        # Totals should match
        assert result1["total"] == result2["total"]
        
        # Different products
        if result1["products"] and result2["products"]:
            asins1 = {p["asin"] for p in result1["products"]}
            asins2 = {p["asin"] for p in result2["products"]}
            assert asins1 != asins2

    def test_text_search_no_query(self):
        """Test search without query (browse)."""
        spec = TextSearchSpec(q="", limit=10)
        result = text_search(spec)
        
        assert isinstance(result["products"], list)
        assert len(result["products"]) <= 10

    def test_text_search_limit_validation(self):
        """Test limit boundaries."""
        # Default limit
        spec = TextSearchSpec(q="test")
        assert spec.limit == 3
        
        # Max limit
        spec = TextSearchSpec(q="test", limit=50)
        assert spec.limit == 50
        
        # Invalid limit should fail validation
        with pytest.raises(Exception):
            TextSearchSpec(q="test", limit=100)

    def test_text_search_response_structure(self):
        """Test response has correct structure."""
        spec = TextSearchSpec(q="laptop", limit=3)
        result = text_search(spec)
        
        assert "products" in result
        assert "total" in result
        assert "debug" in result
        
        # Check product structure
        for product in result["products"]:
            assert "asin" in product
            assert "title" in product
            # Optional fields
            assert "final_price" in product or product.get("final_price") is None
            assert "rating" in product or product.get("rating") is None


class TestRowToCard:
    """Test row to ProductCard conversion."""

    def test_row_to_card_valid(self):
        """Test conversion with valid data."""
        mock_row = {
            "asin": "B123456",
            "title": "Test Product",
            "final_price": 29.99,
            "currency": "USD",
            "rating": 4.5,
            "image_url": "https://example.com/image.jpg",
            "url": "https://example.com/product"
        }
        
        card = _row_to_card(mock_row)
        
        assert card is not None
        assert card.asin == "B123456"
        assert card.title == "Test Product"
        assert card.final_price == 29.99

    def test_row_to_card_minimal(self):
        """Test conversion with minimal required fields."""
        mock_row = {
            "asin": "B123456",
            "title": "Test Product"
        }
        
        card = _row_to_card(mock_row)
        
        assert card is not None
        assert card.asin == "B123456"
        assert card.title == "Test Product"
        assert card.final_price is None

    def test_row_to_card_invalid(self):
        """Test conversion with invalid data."""
        mock_row = {
            "asin": None,
            "title": None
        }
        
        card = _row_to_card(mock_row)
        assert card is None

    def test_row_to_card_missing_fields(self):
        """Test conversion with missing fields."""
        mock_row = {}
        
        card = _row_to_card(mock_row)
        assert card is None


@pytest.mark.requires_db
@pytest.mark.requires_faiss
class TestCatalogSearchEdgeCases:
    """Test edge cases."""

    def test_empty_query(self):
        """Test with empty query."""
        spec = TextSearchSpec(q="", limit=5)
        result = text_search(spec)
        
        assert isinstance(result["products"], list)
        assert result["debug"]["via"] == "no_query"

    def test_special_characters(self):
        """Test with special characters in query."""
        spec = TextSearchSpec(q="test's \"quoted\" & special", limit=5)
        result = text_search(spec)
        
        # Should not crash
        assert isinstance(result["products"], list)

    def test_unicode_query(self):
        """Test with unicode characters."""
        spec = TextSearchSpec(q="café élégant", limit=5)
        result = text_search(spec)
        
        assert isinstance(result["products"], list)

    def test_very_long_query(self):
        """Test with very long query."""
        long_query = " ".join(["word"] * 100)
        spec = TextSearchSpec(q=long_query, limit=5)
        result = text_search(spec)
        
        assert isinstance(result["products"], list)

    def test_nonexistent_products(self):
        """Test search that returns no results."""
        spec = TextSearchSpec(q="xyznonexistent12345", limit=5)
        result = text_search(spec)
        
        # May return empty or very few irrelevant results
        assert isinstance(result["products"], list)
        assert isinstance(result["total"], int)
        assert result["total"] >= 0

    def test_multiple_filters(self):
        """Test with multiple complex filters."""
        spec = TextSearchSpec(
            q="product",
            filters={
                "price_min": 10.0,
                "price_max": 100.0,
                "rating_min": 4.0,
                "rating_max": 5.0,
                "availability": True
            },
            limit=10
        )
        result = text_search(spec)
        
        assert isinstance(result["products"], list)

    def test_invalid_filter_values(self):
        """Test with invalid filter values."""
        spec = TextSearchSpec(
            q="laptop",
            filters={
                "price_min": -100,  # Negative price
                "rating_max": 10    # Invalid rating
            },
            limit=5
        )
        
        # Should handle gracefully
        result = text_search(spec)
        assert isinstance(result["products"], list)

