# Backend Unit Tests

This directory contains unit tests for the healthcare claims backend services.

## Test Files

- `test_claims.py` - Unit tests for the claims service (10 tests)
- `test_notify.py` - Unit tests for the notification service (18 tests)
- `conftest.py` - Pytest configuration and shared fixtures

## Running Tests

### From the Backend Directory (Recommended)

```bash
cd backend
source venv/bin/activate
python -m pytest tests/ -v
```

### From the Tests Directory

```bash
cd backend/tests
source ../venv/bin/activate
python -m pytest -v
```

### Running Specific Tests

```bash
# Run all claims tests
python -m pytest tests/test_claims.py -v

# Run all notification tests
python -m pytest tests/test_notify.py -v

# Run specific test class
python -m pytest tests/test_notify.py::TestNotifyHealth -v

# Run single test
python -m pytest tests/test_claims.py::TestClaimsCRUD::test_create_claim -v
```

## Test Coverage

These unit tests use comprehensive database mocking to ensure:
- Fast execution (no real database connections)
- Reliable results (no external dependencies)
- Isolated testing of individual service components

**Total: 28 unit tests**
- All tests pass without event loop issues
- Comprehensive mocking for database operations
- Tests cover CRUD operations, validation, error handling
