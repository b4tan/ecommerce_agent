# Tests for FAISS Hybrid Search

Clean, focused tests for the Gemini-powered FAISS hybrid search system.

## Test Structure

```
tests/
├── conftest.py              # Fixtures and configuration
├── test_hybrid_search.py    # Core hybrid search tests
├── test_catalog_search.py   # Catalog search API tests
└── test_integration.py      # End-to-end integration tests
```

## Running Tests

### All tests
```bash
pytest tests/
```

### Specific test file
```bash
pytest tests/test_hybrid_search.py
pytest tests/test_catalog_search.py
pytest tests/test_integration.py
```

### By marker
```bash
pytest -m requires_db           # Tests requiring database
pytest -m requires_faiss        # Tests requiring FAISS index
pytest -m requires_api          # Tests requiring API key
```

### Verbose output
```bash
pytest tests/ -v
```

### With coverage
```bash
pytest tests/ --cov=services --cov-report=html
```

## Prerequisites

### 1. Database
```bash
python scripts/build_db.py scripts/amazon-products.csv
```

### 2. FAISS Index
```bash
python scripts/build_faiss_gemini.py
```

### 3. Environment Variables
Create `backend/.env`:
```bash
GOOGLE_API_KEY=your_key_here
```

## Test Categories

### `test_hybrid_search.py`
- Vector search (FAISS)
- Lexical search (SQL LIKE)
- Hybrid ranking
- Filter application
- Pagination
- Edge cases

### `test_catalog_search.py`
- API interface
- Request/response structure
- ProductCard conversion
- Error handling
- Input validation

### `test_integration.py`
- Complete search pipeline
- Tool integration
- Search quality
- Performance
- Robustness

## Test Markers

- `@pytest.mark.requires_db` - Needs database
- `@pytest.mark.requires_faiss` - Needs FAISS index  
- `@pytest.mark.requires_api` - Needs API key

## Expected Test Results

With database and FAISS index:
- ✅ All tests should pass
- ⏱️ Average: ~2-5 seconds total
- 🎯 Coverage: >85%

Without FAISS index:
- ⏭️ Tests marked `requires_faiss` will skip

## Troubleshooting

### "Test database not found"
```bash
python scripts/build_db.py scripts/amazon-products.csv
```

### "FAISS index missing"
```bash
python scripts/build_faiss_gemini.py
```

### "GOOGLE_API_KEY missing"
Set in `backend/.env` or skip API tests:
```bash
pytest tests/ -m "not requires_api"
```

### Import errors
```bash
pip install -r requirements.txt
```

## Adding New Tests

1. Add to appropriate file
2. Use descriptive names
3. Add markers if needed
4. Keep tests independent
5. Clean up resources

Example:
```python
@pytest.mark.requires_db
def test_new_feature(db_connection):
    """Test new feature description."""
    # Test implementation
    assert result == expected
```

