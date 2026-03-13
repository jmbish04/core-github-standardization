# Jules Client - Modular Structure Documentation

## Overview

The Jules client has been refactored into a highly modular structure following the Single Responsibility Principle. This document describes the new organization and how to use it.

## Directory Structure

```
.github/scripts/jules/
├── __init__.py                     # Package entry point with exports
├── jules_client.py                 # Main JulesClient class (orchestrator)
├── jules_helpers.py                # Helper utilities for GitHub Actions
├── config.py                       # Constants and configuration
├── requirements.txt                # Python dependencies
├── pytest.ini                      # Pytest configuration
│
├── data_classes/                   # Data models and enums
│   ├── __init__.py
│   ├── enums/                      # Enumeration types
│   │   ├── __init__.py
│   │   ├── automation_mode.py      # AutomationMode enum
│   │   └── session_state.py        # SessionState enum
│   └── models/                     # Data model classes
│       ├── __init__.py
│       ├── activity.py             # Activity data class
│       ├── dedup_result.py         # DedupResult data class
│       ├── plan.py                 # Plan and PlanStep classes
│       ├── pull_request.py         # PullRequest data class
│       └── session.py              # Session data class
│
├── utils/                          # Utility functions
│   ├── __init__.py
│   ├── deduplication.py            # Session deduplication logic
│   └── logging.py                  # Activity logging utilities
│
├── sources/                        # Source repository operations
│   ├── __init__.py
│   └── sources_api.py              # SourcesAPI class
│
├── sessions/                       # Session management
│   ├── __init__.py
│   ├── sessions_api.py             # SessionsAPI class
│   └── activities_api.py           # ActivitiesAPI class
│
└── tests/                          # Comprehensive test suite
    ├── README.md                   # Testing documentation
    ├── conftest.py                 # Shared test fixtures
    ├── test_config.py              # Config tests
    ├── data_classes/
    │   └── test_data_classes.py    # Data class tests
    ├── utils/
    │   └── test_utils.py           # Utils tests
    ├── sources/
    │   └── test_sources_api.py     # Sources API tests
    └── sessions/
        └── test_sessions_api.py    # Sessions API tests
```

## Module Descriptions

### config.py

Centralizes all constants and configuration values:
- API URLs and endpoints
- Default timeouts and intervals
- Session state definitions
- Pagination settings
- Default prompts

**Example:**
```python
from jules.config import BASE_URL, ACTIVE_STATES, DEFAULT_POLL_INTERVAL
```

### data_classes/

Contains all data models used throughout the client:

#### Enums
- **AutomationMode**: Session automation settings (AUTO_CREATE_PR, etc.)
- **SessionState**: Session lifecycle states (QUEUED, IN_PROGRESS, COMPLETED, etc.)

#### Models
- **Session**: Represents a Jules coding session
- **Activity**: Represents an event in a session
- **Plan/PlanStep**: Execution plan and its steps
- **PullRequest**: GitHub pull request data
- **DedupResult**: Result of deduplication check

**Example:**
```python
from jules import Session, AutomationMode, SessionState

session = Session.from_dict(api_response)
if session.state == SessionState.COMPLETED.value:
    print("Session completed!")
```

### utils/

Reusable utility functions:

#### deduplication.py
- `prompt_fingerprint(prompt)`: Generate SHA-256 fingerprint of prompts
- `check_for_duplicate(...)`: Check if a session already exists

#### logging.py
- `log_activity(activity, log)`: Log activities in human-readable format

**Example:**
```python
from jules.utils import prompt_fingerprint, log_activity

fp = prompt_fingerprint("Generate agent skills")
# fp = "a1b2c3d4e5f6g7h8"

log_activity(activity, print)
# [Jules] Plan generated — 3 step(s):
#          [1] Review codebase
#          [2] Generate skills
#          [3] Create PR
```

### sources/

Manages GitHub repository sources:

#### SourcesAPI
- `list_sources()`: List all connected sources
- `get_source(source_name)`: Get a specific source
- `find_source_for_repo(owner, repo)`: Find source by owner/repo

**Example:**
```python
client = JulesClient()
sources = client.sources.list_sources()
source = client.sources.find_source_for_repo("owner", "repo")
```

### sessions/

Manages Jules sessions and activities:

#### SessionsAPI
- `create_session(...)`: Create a new session
- `get_session(session_id)`: Get session details
- `list_sessions()`: List sessions with pagination
- `approve_plan(session_id)`: Approve a plan
- `send_message(session_id, prompt)`: Send a message
- `check_for_duplicate(...)`: Check for duplicate sessions
- `create_session_safe(...)`: Create session with dedup check
- `run_agent_skills_session(...)`: End-to-end helper for Agent Skills

#### ActivitiesAPI
- `get_activity(session_id, activity_id)`: Get an activity
- `list_activities(session_id)`: List session activities
- `stream_activities(session_id)`: Stream activities in real-time

**Example:**
```python
client = JulesClient()

# Create session with automatic deduplication
session, was_existing = client.sessions.create_session_safe(
    prompt="Generate agent skills",
    source_name="sources/github--owner--repo",
    starting_branch="main"
)

# Stream activities
for activity in client.activities.stream_activities(session.id):
    print(f"Activity: {activity.activity_type}")
```

### jules_client.py

The main orchestrator class that combines all components. Provides convenient access to all APIs through a single interface.

**Example:**
```python
from jules import JulesClient

client = JulesClient()  # Uses JULES_API_KEY env var

# Convenience methods delegate to sub-APIs
sources = client.list_sources()
session = client.create_session(...)
activities = client.list_activities(session_id)

# Or access sub-APIs directly
source = client.sources.get_source("sources/github--owner--repo")
session = client.sessions.get_session("session123")
```

## Testing

### Running Tests

```bash
cd .github/scripts/jules
pip install -r requirements.txt
pytest
```

### Test Coverage

```bash
pytest --cov=. --cov-report=term-missing
pytest --cov=. --cov-report=html  # Generate HTML report
```

### Test Structure

- **conftest.py**: Shared fixtures for test data
- **test_config.py**: Tests for configuration constants
- **data_classes/test_data_classes.py**: Tests for all data classes
- **utils/test_utils.py**: Tests for utility functions
- **sources/test_sources_api.py**: Tests for SourcesAPI
- **sessions/test_sessions_api.py**: Tests for SessionsAPI

See `tests/README.md` for detailed testing documentation.

## Migration Guide

### Old Code

```python
from jules import JulesClient

client = JulesClient()
session = client.create_session(
    prompt="Test",
    source_name="sources/github--owner--repo",
    starting_branch="main"
)
```

### New Code

**The API remains backward compatible!** All existing code continues to work:

```python
from jules import JulesClient

client = JulesClient()
session = client.create_session(
    prompt="Test",
    source_name="sources/github--owner--repo",
    starting_branch="main"
)
```

### New Features

You can now also use the modular APIs directly:

```python
from jules import JulesClient

client = JulesClient()

# Access sub-APIs
sources_api = client.sources
sessions_api = client.sessions
activities_api = client.activities

# Use them independently
source = sources_api.find_source_for_repo("owner", "repo")
session = sessions_api.create_session_safe(...)
activities = activities_api.list_activities(session.id)
```

## Benefits of the New Structure

### 1. Modularity
- Each module has a single, well-defined responsibility
- Easy to understand, test, and maintain
- Changes to one module don't affect others

### 2. Testability
- Comprehensive test suite with 10+ tests
- Easy to mock dependencies
- High test coverage

### 3. Reusability
- Utility functions can be imported and used independently
- Data classes are decoupled from API logic
- Components can be mixed and matched

### 4. Maintainability
- Clear separation of concerns
- Comprehensive documentation and type hints
- Follows PEP 8 standards

### 5. Extensibility
- Easy to add new endpoints or features
- New utilities can be added to utils/
- New data models can be added to data_classes/

## Type Hints

All functions include comprehensive type hints:

```python
def create_session(
    self,
    prompt: str,
    source_name: str,
    starting_branch: str = "main",
    title: Optional[str] = None,
    require_plan_approval: bool = False,
    automation_mode: AutomationMode = AutomationMode.AUTO_CREATE_PR,
) -> Session:
    ...
```

## Error Handling

The client raises appropriate exceptions:
- `EnvironmentError`: Missing JULES_API_KEY
- `requests.HTTPError`: HTTP errors from the API
- `RuntimeError`: Session failures or invalid states

## Environment Variables

- `JULES_API_KEY`: Required - Your Google API key with Jules API access

## Dependencies

Core dependencies (see `requirements.txt`):
- `requests>=2.31.0`: HTTP client

Testing dependencies:
- `pytest>=7.4.0`: Test runner
- `pytest-cov>=4.1.0`: Coverage reporting
- `pytest-mock>=3.11.1`: Mocking utilities

Development dependencies:
- `black>=23.7.0`: Code formatter
- `flake8>=6.1.0`: Linter
- `mypy>=1.5.0`: Type checker

## Contributing

When adding new functionality:

1. Create new modules in the appropriate directory
2. Add type hints to all functions
3. Write comprehensive tests
4. Update this documentation
5. Run tests and ensure coverage remains high

## Version History

- **v2.0.0**: Modularized structure with comprehensive testing
- **v1.0.0**: Original monolithic structure

## Support

For issues or questions:
- Check the test files for usage examples
- Review the type hints and docstrings
- See the comprehensive test suite in `tests/`
