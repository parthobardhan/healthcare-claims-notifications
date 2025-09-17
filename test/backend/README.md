# Backend Tests

This directory contains all the backend test files for the healthcare claims application.

## Test Files

- `test_claims.py` - Unit tests for the claims service
- `test_notify.py` - Unit tests for the notification service
- `test_integration.py` - Integration tests for both services working together
- `conftest.py` - Pytest configuration and shared fixtures

## Running Tests

### From the Backend Directory (Recommended)

```bash
cd backend
source venv/bin/activate
python -m pytest ../test/backend/ -v
```

### From the Test Directory

```bash
cd test/backend
./run_tests.sh -v
```

### Running Specific Tests

```bash
# From backend directory
python -m pytest ../test/backend/test_notify.py::TestNotifyHealth::test_health_endpoint -v

# From test directory
./run_tests.sh test_notify.py::TestNotifyHealth::test_health_endpoint -v
```

## Test Coverage

All tests use database mocking to avoid event loop issues and ensure fast, reliable execution. The tests cover:

- Claims CRUD operations
- Notification service functionality
- Integration between claims and notification services
- Error handling and edge cases

Total: 38 tests across all services.
