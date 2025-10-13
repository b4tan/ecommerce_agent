"""Test fixtures and configuration."""
import os
import pytest
import sqlite3
import tempfile
import shutil

# Test database path
TEST_DB_PATH = os.getenv("TEST_DB_PATH", "./data/catalog.sqlite")
TEST_FAISS_DIR = os.getenv("TEST_FAISS_DIR", "./data/faiss")

# Check if test resources exist
DB_EXISTS = os.path.exists(TEST_DB_PATH)
FAISS_EXISTS = os.path.exists(os.path.join(TEST_FAISS_DIR, "index.faiss"))


@pytest.fixture
def test_db_path():
    """Provide test database path."""
    return TEST_DB_PATH


@pytest.fixture
def db_connection():
    """Provide a database connection for tests."""
    if not DB_EXISTS:
        pytest.skip("Test database not found")
    
    conn = sqlite3.connect(TEST_DB_PATH)
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()


@pytest.fixture
def sample_product(db_connection):
    """Get a sample product from the database."""
    row = db_connection.execute(
        "SELECT * FROM products LIMIT 1"
    ).fetchone()
    return dict(row) if row else None


@pytest.fixture
def sample_products(db_connection):
    """Get multiple sample products."""
    rows = db_connection.execute(
        "SELECT * FROM products LIMIT 10"
    ).fetchall()
    return [dict(r) for r in rows]


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "requires_db: mark test as requiring database"
    )
    config.addinivalue_line(
        "markers", "requires_faiss: mark test as requiring FAISS index"
    )
    config.addinivalue_line(
        "markers", "requires_api: mark test as requiring API key"
    )

