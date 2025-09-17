# Integration Tests

This directory contains integration tests for the healthcare claims application, testing the interaction between claims and notification services.

## Test Files

- `test_integration.py` - Integration tests for both services working together (10 tests)

## Running Tests

### From the Integration Directory

```bash
cd test/integration
./run_tests.sh -v
```

### From the Root Directory

```bash
# Activate backend virtual environment
source backend/venv/bin/activate

# Set Python path and run tests
PYTHONPATH=backend python -m pytest test/integration/ -v
```

### Running Specific Tests

```bash
# From integration directory
./run_tests.sh test_integration.py::TestClaimsNotificationIntegration -v

# From root directory
PYTHONPATH=backend python -m pytest test/integration/test_integration.py::TestServiceHealthChecks -v
```

## Test Coverage

Integration tests cover:
- Claims status changes triggering notifications
- Cross-service communication between claims and notifications
- Error handling when services are unavailable
- End-to-end notification delivery workflows
- Health checks for all services

**Total: 10 integration tests**
- Uses database mocking for reliable execution
- Tests real API interactions between services
- Verifies complete notification workflows
