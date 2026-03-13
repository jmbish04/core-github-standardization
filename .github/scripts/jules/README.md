# Jules Service Module

Modular Python client and utilities for interacting with the Jules REST API.

## Overview

This package provides a clean, well-documented interface to the Jules API with built-in deduplication logic to prevent duplicate session creation in GitHub Actions workflows.

## Structure

```
jules/
├── __init__.py           # Package initialization and exports
├── jules_client.py       # Core JulesClient class and data models
├── jules_helpers.py      # Helper functions for common operations
└── README.md            # This file
```

## Components

### jules_client.py

Contains the main `JulesClient` class for interacting with the Jules REST API:

- **JulesClient**: Full-featured REST API client
  - Session management (create, get, list)
  - Activity streaming and monitoring
  - Deduplication logic to prevent redundant sessions
  - High-level convenience methods

- **Data Models**:
  - `Session`: Represents a Jules session
  - `Activity`: Represents a session activity
  - `Plan`: Represents a generated plan
  - `PlanStep`: Individual step in a plan
  - `PullRequest`: Pull request information
  - `DedupResult`: Result of duplicate checking

- **Enums**:
  - `AutomationMode`: Session automation settings
  - `SessionState`: Session state values

### jules_helpers.py

Utility functions for common GitHub Actions integration patterns:

- `get_repo_context()`: Extract repository information from environment
- `create_skill_files()`: Create agent skills in multiple locations
- `create_instruction_files()`: Create agent instruction files
- `get_jules_source_name()`: Format Jules source names
- `parse_jules_source_name()`: Parse Jules source names

## Usage

### Basic Session Creation

```python
from jules import JulesClient

# Initialize the client (reads JULES_API_KEY from environment)
client = JulesClient()

# Create a session
session = client.create_session(
    prompt="Generate agent skills for this repository",
    source_name="sources/github--owner--repo",
    starting_branch="main"
)

print(f"Session created: {session.url}")
```

### Using Helper Functions

```python
from jules import JulesClient
from jules.jules_helpers import get_repo_context, get_jules_source_name

# Get repository context from GitHub Actions environment
context = get_repo_context()
source_name = get_jules_source_name(context["owner"], context["repo"])

# Create client and run session
client = JulesClient()
pr_url = client.run_agent_skills_session(
    source_name=source_name,
    starting_branch=context["branch"]
)
```

### Deduplication

The client includes built-in deduplication to prevent multiple GitHub Actions runs from creating redundant sessions:

```python
# Automatically skips if an active session with the same prompt exists
session, was_existing = client.create_session_safe(
    prompt="Generate agent skills",
    source_name="sources/github--owner--repo",
    starting_branch="main",
    block_active_only=True  # Only block if session is active
)

if was_existing:
    print("Reusing existing session")
else:
    print("Created new session")
```

## Environment Variables

- `JULES_API_KEY`: Required. Your Jules API key
- `GITHUB_REPOSITORY`: Used by helpers to extract repository context
- `GITHUB_REF`: Used by helpers to extract branch information

## Examples

See the following scripts for complete usage examples:

- `../jules-generate-agent-skills-python.py`: Generates agent skills
- `../jules-generate-agent-instructions.py`: Generates agent instructions
- `../jules-cloudflare-fix.py`: Analyzes and fixes Cloudflare build errors

## API Documentation

For complete API documentation, see the docstrings in:
- `jules_client.py`: Core client and session management
- `jules_helpers.py`: Helper functions and utilities
