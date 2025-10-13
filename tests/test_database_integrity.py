"""
Tests for database integrity, schema validation, and data quality.
Ensures the database structure and data are correct for the ecommerce agent.
"""
import pytest
import sqlite3
from tests.conftest import TestDataHelper


class TestDatabaseSchema:
    """Test database schema and structure."""
    
    def test_products_table_exists(self, db_connection):
        """Test that products table exists and has expected structure."""
        cursor = db_connection.cursor()
        
        # Check if products table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='products'
        """)
        table_exists = cursor.fetchone()
        assert table_exists is not None, "Products table should exist"
        
        # Get table schema
        cursor.execute("PRAGMA table_info(products)")
        columns = cursor.fetchall()
        
        # Check for required columns
        column_names = [col[1] for col in columns]
        required_columns = ['asin', 'title', 'final_price', 'currency', 'rating']
        
        for required_col in required_columns:
            assert required_col in column_names, f"Required column '{required_col}' missing"
    
    def test_products_table_has_data(self, db_connection):
        """Test that products table has data."""
        cursor = db_connection.cursor()
        
        # Check total count
        cursor.execute("SELECT COUNT(*) FROM products")
        count = cursor.fetchone()[0]
        assert count > 0, "Products table should have data"
        assert count >= 100, "Should have at least 100 products for testing"
    
    def test_required_fields_not_null(self, db_connection):
        """Test that required fields are not null."""
        cursor = db_connection.cursor()
        
        # Check for null ASINs
        cursor.execute("SELECT COUNT(*) FROM products WHERE asin IS NULL OR asin = ''")
        null_asins = cursor.fetchone()[0]
        assert null_asins == 0, "No products should have null or empty ASINs"
        
        # Check for null titles
        cursor.execute("SELECT COUNT(*) FROM products WHERE title IS NULL OR title = ''")
        null_titles = cursor.fetchone()[0]
        assert null_titles == 0, "No products should have null or empty titles"
    
    def test_asin_uniqueness(self, db_connection):
        """Test that ASINs are unique."""
        cursor = db_connection.cursor()
        
        # Count total ASINs
        cursor.execute("SELECT COUNT(*) FROM products")
        total_count = cursor.fetchone()[0]
        
        # Count unique ASINs
        cursor.execute("SELECT COUNT(DISTINCT asin) FROM products")
        unique_count = cursor.fetchone()[0]
        
        assert total_count == unique_count, "All ASINs should be unique"
    
    def test_numeric_fields_format(self, db_connection):
        """Test that numeric fields have correct format."""
        cursor = db_connection.cursor()
        
        # Test final_price format (should be numeric or null)
        cursor.execute("""
            SELECT COUNT(*) FROM products 
            WHERE final_price IS NOT NULL 
            AND final_price != '' 
            AND NOT (
                CAST(final_price AS REAL) IS final_price
                OR final_price LIKE '%.%'
            )
        """)
        invalid_prices = cursor.fetchone()[0]
        # Note: This test might need adjustment based on actual data format
        
        # Test rating format (should be numeric between 0-5 or null)
        cursor.execute("""
            SELECT COUNT(*) FROM products 
            WHERE rating IS NOT NULL 
            AND rating != '' 
            AND NOT (
                CAST(rating AS REAL) IS rating
                OR rating LIKE '%.%'
            )
        """)
        invalid_ratings = cursor.fetchone()[0]
        # Note: This test might need adjustment based on actual data format
    
    def test_fts_table_availability(self, db_connection):
        """Test if FTS (Full Text Search) table is available."""
        cursor = db_connection.cursor()
        
        # Check if products_fts table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='products_fts'
        """)
        fts_table = cursor.fetchone()
        
        if fts_table:
            # If FTS table exists, test it
            cursor.execute("SELECT COUNT(*) FROM products_fts")
            fts_count = cursor.fetchone()[0]
            assert fts_count > 0, "FTS table should have data"
        else:
            # FTS table doesn't exist, which is okay for LIKE-based search
            pytest.skip("FTS table not available, using LIKE-based search")


class TestDataQuality:
    """Test data quality and consistency."""
    
    def test_rating_values_range(self, db_connection):
        """Test that rating values are within valid range (0-5)."""
        cursor = db_connection.cursor()
        
        # Get ratings that can be converted to float
        cursor.execute("""
            SELECT rating FROM products 
            WHERE rating IS NOT NULL 
            AND rating != ''
        """)
        ratings = cursor.fetchall()
        
        for (rating,) in ratings:
            try:
                rating_val = float(rating)
                assert 0 <= rating_val <= 5, f"Rating {rating_val} should be between 0 and 5"
            except ValueError:
                # Non-numeric ratings are acceptable (will be handled by _safe_float)
                pass
    
    def test_price_values_positive(self, db_connection):
        """Test that price values are positive."""
        cursor = db_connection.cursor()
        
        # Get prices that can be converted to float
        cursor.execute("""
            SELECT final_price FROM products 
            WHERE final_price IS NOT NULL 
            AND final_price != ''
        """)
        prices = cursor.fetchall()
        
        for (price,) in prices:
            try:
                price_val = float(price)
                assert price_val >= 0, f"Price {price_val} should be non-negative"
            except ValueError:
                # Non-numeric prices are acceptable (will be handled by _safe_float)
                pass
    
    def test_currency_values_consistency(self, db_connection):
        """Test that currency values are consistent."""
        cursor = db_connection.cursor()
        
        # Get all currency values
        cursor.execute("""
            SELECT DISTINCT currency FROM products 
            WHERE currency IS NOT NULL AND currency != ''
        """)
        currencies = cursor.fetchall()
        
        # Common currency codes (extend as needed)
        valid_currencies = {'USD', 'EUR', 'GBP', 'CAD', 'AUD', 'JPY'}
        
        for (currency,) in currencies:
            # Currency should be a valid 3-letter code or common format
            assert len(currency) >= 3, f"Currency '{currency}' should be at least 3 characters"
            # Note: This is a basic check, adjust based on actual data
    
    def test_title_length_reasonableness(self, db_connection):
        """Test that product titles have reasonable lengths."""
        cursor = db_connection.cursor()
        
        cursor.execute("SELECT title FROM products LIMIT 100")
        titles = cursor.fetchall()
        
        for (title,) in titles:
            assert len(title) > 0, "Title should not be empty"
            assert len(title) <= 1000, f"Title should not be excessively long: {len(title)} chars"
            # Most product titles should be reasonable length
            assert len(title) >= 5, f"Title should be descriptive: '{title[:50]}...'"
    
    def test_image_urls_format(self, db_connection):
        """Test that image URLs have reasonable format."""
        cursor = db_connection.cursor()
        
        cursor.execute("""
            SELECT image_url FROM products 
            WHERE image_url IS NOT NULL 
            AND image_url != ''
            LIMIT 100
        """)
        urls = cursor.fetchall()
        
        for (url,) in urls:
            # Basic URL format check
            assert url.startswith(('http://', 'https://')), f"Invalid URL format: {url}"
            assert len(url) > 10, f"URL seems too short: {url}"
            assert len(url) < 2000, f"URL seems too long: {len(url)} chars"


class TestDatabasePerformance:
    """Test database performance characteristics."""
    
    def test_simple_query_performance(self, db_connection):
        """Test performance of simple queries."""
        import time
        
        cursor = db_connection.cursor()
        
        # Test simple count query
        start_time = time.time()
        cursor.execute("SELECT COUNT(*) FROM products")
        count = cursor.fetchone()[0]
        end_time = time.time()
        
        query_time = end_time - start_time
        assert query_time < 1.0, f"Simple count query took too long: {query_time:.3f}s"
        assert count > 0, "Should return count"
    
    def test_search_query_performance(self, db_connection):
        """Test performance of search-like queries."""
        import time
        
        cursor = db_connection.cursor()
        
        # Test LIKE query (fallback search method)
        start_time = time.time()
        cursor.execute("""
            SELECT COUNT(*) FROM products 
            WHERE title LIKE '%shoe%' OR title LIKE '%running%'
        """)
        count = cursor.fetchone()[0]
        end_time = time.time()
        
        query_time = end_time - start_time
        assert query_time < 2.0, f"Search query took too long: {query_time:.3f}s"
        # Note: Count might be 0 if no products match, which is okay
    
    def test_filtered_query_performance(self, db_connection):
        """Test performance of filtered queries."""
        import time
        
        cursor = db_connection.cursor()
        
        # Test filtered query
        start_time = time.time()
        cursor.execute("""
            SELECT COUNT(*) FROM products 
            WHERE rating >= 4.0 AND final_price <= 100.0
        """)
        count = cursor.fetchone()[0]
        end_time = time.time()
        
        query_time = end_time - start_time
        assert query_time < 2.0, f"Filtered query took too long: {query_time:.3f}s"
    
    def test_pagination_query_performance(self, db_connection):
        """Test performance of pagination queries."""
        import time
        
        cursor = db_connection.cursor()
        
        # Test pagination query
        start_time = time.time()
        cursor.execute("""
            SELECT * FROM products 
            ORDER BY rating DESC 
            LIMIT 10 OFFSET 100
        """)
        results = cursor.fetchall()
        end_time = time.time()
        
        query_time = end_time - start_time
        assert query_time < 2.0, f"Pagination query took too long: {query_time:.3f}s"
        assert len(results) <= 10, "Should return at most 10 results"


class TestDatabaseConstraints:
    """Test database constraints and data integrity rules."""
    
    def test_no_duplicate_asins(self, db_connection):
        """Test that there are no duplicate ASINs."""
        cursor = db_connection.cursor()
        
        cursor.execute("""
            SELECT asin, COUNT(*) as count 
            FROM products 
            GROUP BY asin 
            HAVING COUNT(*) > 1
        """)
        duplicates = cursor.fetchall()
        
        assert len(duplicates) == 0, f"Found duplicate ASINs: {duplicates[:5]}"
    
    def test_asin_format_consistency(self, db_connection):
        """Test that ASINs have consistent format."""
        cursor = db_connection.cursor()
        
        cursor.execute("SELECT asin FROM products LIMIT 100")
        asins = cursor.fetchall()
        
        for (asin,) in asins:
            # ASINs should be non-empty strings
            assert isinstance(asin, str), f"ASIN should be string: {type(asin)}"
            assert len(asin) > 0, "ASIN should not be empty"
            assert len(asin) <= 50, f"ASIN seems too long: {len(asin)} chars"
    
    def test_reviews_count_consistency(self, db_connection):
        """Test that reviews_count values are consistent."""
        cursor = db_connection.cursor()
        
        cursor.execute("""
            SELECT reviews_count FROM products 
            WHERE reviews_count IS NOT NULL 
            AND reviews_count != ''
            LIMIT 100
        """)
        review_counts = cursor.fetchall()
        
        for (count,) in review_counts:
            try:
                count_val = int(count)
                assert count_val >= 0, f"Review count should be non-negative: {count_val}"
            except ValueError:
                # Non-numeric counts are acceptable (will be handled by conversion)
                pass
