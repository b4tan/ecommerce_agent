# Ecommerce Agent Test Suite

This directory contains a comprehensive test suite for the ecommerce agent system, designed to ensure the tools, database search, and API layers work correctly for the agent.

## Test Structure

### Core Test Files
- **`conftest.py`** - Test configuration, fixtures, and utilities
- **`tool_test.py`** - Basic tests for the product search tool
- **`catalog_api_test.py`** - Basic tests for the catalog API
- **`catalog_search_test.py`** - Basic tests for database search functionality

### Comprehensive Test Files
- **`test_tool_comprehensive.py`** - Extensive tests for tool functionality, input validation, error handling, and edge cases
- **`test_catalog_api_comprehensive.py`** - Comprehensive API tests including boundary conditions and error scenarios
- **`test_catalog_search_comprehensive.py`** - Thorough database search tests with various query combinations
- **`test_database_integrity.py`** - Database schema, data quality, and performance tests
- **`test_integration.py`** - End-to-end integration tests and system reliability tests

## Test Categories

### 1. Basic Functionality Tests
- Tool invocation with valid inputs
- API search and product retrieval
- Database search with basic queries
- Result structure validation

### 2. Input Validation Tests
- Invalid payload handling
- Parameter type validation
- Boundary value testing
- Malformed input scenarios

### 3. Error Handling Tests
- Database connection failures
- Search execution errors
- Tool input validation errors
- Graceful degradation testing

### 4. Edge Case Tests
- Very long queries
- Special characters and Unicode
- Empty and null inputs
- Extreme parameter values

### 5. Performance Tests
- Query execution time
- Memory usage validation
- Concurrent access testing
- Large result set handling

### 6. Integration Tests
- End-to-end workflows
- Cross-layer consistency
- Real-world scenarios
- System reliability

### 7. Database Integrity Tests
- Schema validation
- Data quality checks
- Constraint verification
- Performance benchmarks

## Test Utilities

### TestDataHelper Class
Provides utility methods for:
- Creating valid test payloads
- Asserting result structure validity
- Validating product card format
- Generating test data combinations

### Fixtures
- **`db_connection`** - Database connection for tests
- **`sample_product_data`** - Sample product data for mocking
- **`mock_product_row`** - Mock database row for testing
- **`text_search_spec`** - Basic search specification

### Test Data Sets
- **`SEARCH_QUERIES`** - Various query strings for testing
- **`FILTER_COMBINATIONS`** - Different filter combinations
- **`SORT_SPECS`** - Various sorting specifications
- **`INVALID_INPUTS`** - Invalid input scenarios

## Running Tests

### Run All Tests
```bash
python -m pytest tests/ -v
```

### Run Specific Test Categories
```bash
# Basic functionality tests
python -m pytest tests/tool_test.py tests/catalog_api_test.py tests/catalog_search_test.py -v

# Comprehensive tests
python -m pytest tests/test_*_comprehensive.py -v

# Integration tests
python -m pytest tests/test_integration.py -v

# Database integrity tests
python -m pytest tests/test_database_integrity.py -v
```

### Run Tests with Coverage
```bash
python -m pytest tests/ --cov=services --cov=backend --cov-report=html
```

## Test Requirements

### Database
- SQLite database at `./data/catalog.sqlite`
- Products table with sample data
- Optional FTS (Full Text Search) table

### Dependencies
- pytest
- unittest.mock
- sqlite3 (built-in)
- All project dependencies from requirements.txt

## Test Coverage

The test suite covers:

✅ **Tool Layer**
- Input validation and sanitization
- Error handling and graceful degradation
- Output format consistency
- Performance and memory usage

✅ **API Layer**
- Parameter validation and clamping
- Search functionality
- Product retrieval
- Error propagation

✅ **Database Search**
- Query execution
- Filter application
- Sorting functionality
- Pagination support

✅ **Integration**
- Cross-layer communication
- Data consistency
- End-to-end workflows
- System reliability

✅ **Edge Cases**
- Invalid inputs
- Extreme values
- Special characters
- Concurrent access

## Best Practices

1. **Isolation** - Each test is independent and can run in any order
2. **Mocking** - External dependencies are mocked where appropriate
3. **Data Validation** - All inputs and outputs are validated
4. **Error Scenarios** - Both success and failure paths are tested
5. **Performance** - Tests include performance and resource usage validation
6. **Documentation** - All tests are well-documented with clear descriptions

## Maintenance

- Add new tests for new functionality
- Update existing tests when APIs change
- Monitor test performance and optimize as needed
- Keep test data up to date with schema changes
- Review and update test coverage regularly
