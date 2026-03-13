# Jules Client Testing

This directory contains comprehensive unit tests for the Jules client package.

## Test Structure

```
tests/
├── conftest.py              # Shared fixtures and test configuration
├── test_config.py           # Tests for config module
├── data_classes/
│   └── test_data_classes.py # Tests for all data classes
├── utils/
│   └── test_utils.py        # Tests for utility functions
├── sources/
│   └── test_sources_api.py  # Tests for SourcesAPI
└── sessions/
    └── test_sessions_api.py # Tests for SessionsAPI
```

## Running Tests

### Install Dependencies

First, install the testing dependencies:

```bash
cd .github/scripts/jules
pip install -r requirements.txt
```

### Run All Tests

```bash
pytest
```

### Run with Coverage

```bash
pytest --cov=. --cov-report=term-missing
```

### Run Specific Test Files

```bash
# Test config module
pytest tests/test_config.py

# Test data classes
pytest tests/data_classes/

# Test utilities
pytest tests/utils/

# Test sources API
pytest tests/sources/

# Test sessions API
pytest tests/sessions/
```

### Run Specific Test Classes or Functions

```bash
# Run a specific test class
pytest tests/data_classes/test_data_classes.py::TestSession

# Run a specific test function
pytest tests/utils/test_utils.py::TestPromptFingerprint::test_same_prompt_same_fingerprint
```

## Test Coverage

The test suite aims for high code coverage across all modules:

- **config.py**: Tests for all constants and configuration values
- **Data classes**: Tests for serialization, properties, and edge cases
- **Utils**: Tests for deduplication and logging functions
- **Sources API**: Tests for all source-related operations
- **Sessions API**: Tests for session management and workflows
- **Activities API**: Tests for activity streaming and polling

## Writing New Tests

When adding new functionality:

1. Create tests in the appropriate subdirectory
2. Use fixtures from `conftest.py` for common test data
3. Mock external dependencies (HTTP requests, etc.)
4. Test edge cases and error conditions
5. Ensure all new code is covered by tests

### Example Test

```python
import pytest
from ..your_module import YourClass

class TestYourClass:
    """Tests for YourClass."""

    @pytest.fixture
    def your_instance(self):
        """Create a YourClass instance."""
        return YourClass()

    def test_your_method(self, your_instance):
        """Test that your_method works correctly."""
        result = your_instance.your_method("input")
        assert result == "expected output"
```

## Mocking External Dependencies

The tests use `unittest.mock` to mock HTTP requests and external dependencies:

```python
from unittest.mock import Mock, patch

def test_with_mocked_request():
    """Test with mocked HTTP request."""
    with patch('requests.Session.get') as mock_get:
        mock_get.return_value.json.return_value = {"data": "value"}
        # Your test code here
```

## Coverage Reports

Coverage reports are generated in multiple formats:

- **Terminal**: Displayed after running tests with `--cov`
- **HTML**: Generated in `htmlcov/` directory
- **XML**: Generated as `coverage.xml` for CI/CD integration

View the HTML report:

```bash
pytest --cov=. --cov-report=html
open htmlcov/index.html
```

## Continuous Integration

Tests should be run in CI/CD pipelines:

```yaml
- name: Run tests
  run: |
    cd .github/scripts/jules
    pip install -r requirements.txt
    pytest --cov=. --cov-report=xml
```

## Test Fixtures

Common fixtures are defined in `conftest.py`:

- `sample_session_dict`: Sample session data from API
- `sample_activity_dict`: Sample activity data from API
- `sample_pull_request_dict`: Sample PR data from API
- `sample_plan_dict`: Sample plan data from API

Use these fixtures in your tests:

```python
def test_example(sample_session_dict):
    """Test using sample session data."""
    session = Session.from_dict(sample_session_dict)
    assert session.id == "test123"
```

## Best Practices

1. **Test isolation**: Each test should be independent
2. **Clear assertions**: Use descriptive assertion messages
3. **Edge cases**: Test boundary conditions and error paths
4. **Mocking**: Mock external dependencies to avoid network calls
5. **Documentation**: Add docstrings to test classes and functions
6. **Naming**: Use descriptive test names that explain what's being tested
