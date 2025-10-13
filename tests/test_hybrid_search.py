"""Tests for hybrid_search.py"""
import pytest
import os
from unittest.mock import patch, MagicMock
import numpy as np


@pytest.mark.requires_db
@pytest.mark.requires_faiss
class TestHybridSearch:
    """Test hybrid search functionality."""

    def test_hybrid_search_with_query(self, db_connection):
        """Test hybrid search returns results."""
        from services.hybrid_search import hybrid_search
        
        rows, total, debug = hybrid_search(
            q="laptop",
            filters={},
            limit=5,
            offset=0
        )
        
        assert isinstance(rows, list)
        assert isinstance(total, int)
        assert isinstance(debug, dict)
        assert debug["via"] == "faiss_hybrid"

    def test_hybrid_search_no_query(self, db_connection):
        """Test hybrid search without query (browse mode)."""
        from services.hybrid_search import hybrid_search
        
        rows, total, debug = hybrid_search(
            q="",
            filters={},
            limit=5,
            offset=0
        )
        
        assert isinstance(rows, list)
        assert debug["via"] == "no_query"

    def test_hybrid_search_with_filters(self, db_connection):
        """Test hybrid search with price and rating filters."""
        from services.hybrid_search import hybrid_search
        
        rows, total, debug = hybrid_search(
            q="shirt",
            filters={
                "price_min": 10.0,
                "price_max": 50.0,
                "rating_min": 4.0
            },
            limit=5,
            offset=0
        )
        
        assert isinstance(rows, list)
        # Check filters were applied
        for row in rows:
            try:
                if row["final_price"]:
                    assert row["final_price"] >= 10.0
                    assert row["final_price"] <= 50.0
            except (KeyError, TypeError):
                pass
            try:
                if row["rating"]:
                    assert row["rating"] >= 4.0
            except (KeyError, TypeError):
                pass

    def test_hybrid_search_pagination(self, db_connection):
        """Test pagination works correctly."""
        from services.hybrid_search import hybrid_search
        
        # Get first page
        rows1, total1, _ = hybrid_search(
            q="product",
            filters={},
            limit=3,
            offset=0
        )
        
        # Get second page
        rows2, total2, _ = hybrid_search(
            q="product",
            filters={},
            limit=3,
            offset=3
        )
        
        assert total1 == total2  # Total should be same
        assert len(rows1) <= 3
        assert len(rows2) <= 3
        
        # Check different results
        if rows1 and rows2:
            asins1 = {r["asin"] for r in rows1}
            asins2 = {r["asin"] for r in rows2}
            assert asins1 != asins2  # Different pages

    @pytest.mark.requires_api
    def test_embed_query(self):
        """Test query embedding."""
        from services.hybrid_search import _embed_query
        
        if not os.getenv("GOOGLE_API_KEY"):
            pytest.skip("GOOGLE_API_KEY not set")
        
        embedding = _embed_query("test query")
        
        assert isinstance(embedding, np.ndarray)
        assert embedding.shape[0] == 1  # Single query
        assert embedding.shape[1] == 768  # Gemini embedding dimension

    def test_lexical_search(self, db_connection):
        """Test lexical search functionality."""
        from services.hybrid_search import _lexical_asins
        
        asins = _lexical_asins(db_connection, "laptop computer", k=10)
        
        assert isinstance(asins, set)
        assert len(asins) <= 10

    def test_normalize_rating(self):
        """Test rating normalization."""
        from services.hybrid_search import _nr_rating
        
        assert _nr_rating(5.0) == 1.0
        assert _nr_rating(0.0) == 0.0
        assert _nr_rating(2.5) == 0.5
        assert _nr_rating(None) == 0.0

    def test_normalize_reviews(self):
        """Test review count normalization."""
        from services.hybrid_search import _nr_reviews
        
        assert _nr_reviews(0) == 0.0
        assert _nr_reviews(50000) >= 0.99  # Log scale
        assert _nr_reviews(None) == 0.0


@pytest.mark.requires_db
class TestHybridSearchEdgeCases:
    """Test edge cases in hybrid search."""

    def test_empty_results(self, db_connection):
        """Test handling of no results."""
        from services.hybrid_search import hybrid_search
        
        rows, total, debug = hybrid_search(
            q="xyzabc123nonexistent",
            filters={},
            limit=5,
            offset=0
        )
        
        # May return empty or very few irrelevant results
        assert isinstance(rows, list)
        assert isinstance(total, int)
        assert total >= 0

    def test_special_characters_in_query(self, db_connection):
        """Test handling of special characters."""
        from services.hybrid_search import hybrid_search
        
        # Should not crash
        rows, total, debug = hybrid_search(
            q="test's \"quote\" & special",
            filters={},
            limit=5,
            offset=0
        )
        
        assert isinstance(rows, list)
        assert isinstance(total, int)

    def test_very_long_query(self, db_connection):
        """Test handling of very long queries."""
        from services.hybrid_search import hybrid_search
        
        long_query = " ".join(["word"] * 100)
        
        rows, total, debug = hybrid_search(
            q=long_query,
            filters={},
            limit=5,
            offset=0
        )
        
        assert isinstance(rows, list)

    def test_invalid_filters(self, db_connection):
        """Test handling of invalid filters."""
        from services.hybrid_search import hybrid_search
        
        # Should handle gracefully
        rows, total, debug = hybrid_search(
            q="laptop",
            filters={
                "price_min": "not_a_number",
                "invalid_key": "invalid_value"
            },
            limit=5,
            offset=0
        )
        
        assert isinstance(rows, list)

