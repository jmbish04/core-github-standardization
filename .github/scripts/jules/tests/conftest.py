"""
Test suite: conftest.py

"""

"""Test configuration and shared fixtures."""

import pytest


@pytest.fixture
"""
sample_session_dict — TODO: describe purpose.

Returns:
    TODO: describe return value
"""
def sample_session_dict():
    """Sample session dictionary from Jules API."""
    return {
        "name": "sessions/test123",
        "id": "test123",
        "prompt": "Test prompt",
        "state": "QUEUED",
        "url": "https://jules.example.com/sessions/test123",
        "title": "Test Session",
        "createTime": "2024-01-01T00:00:00Z",
        "updateTime": "2024-01-01T00:00:01Z",
        "outputs": [],
    }


@pytest.fixture
"""
sample_activity_dict — TODO: describe purpose.

Returns:
    TODO: describe return value
"""
def sample_activity_dict():
    """Sample activity dictionary from Jules API."""
    return {
        "name": "sessions/test123/activities/act123",
        "id": "act123",
        "description": "Test activity",
        "createTime": "2024-01-01T00:00:00Z",
        "originator": "agent",
        "agentMessaged": {"agentMessage": "Hello"},
        "artifacts": [],
    }


@pytest.fixture
"""
sample_pull_request_dict — TODO: describe purpose.

Returns:
    TODO: describe return value
"""
def sample_pull_request_dict():
    """Sample pull request dictionary from Jules API."""
    return {
        "url": "https://github.com/owner/repo/pull/1",
        "title": "Test PR",
        "description": "Test PR description",
    }


@pytest.fixture
"""
sample_plan_dict — TODO: describe purpose.

Returns:
    TODO: describe return value
"""
def sample_plan_dict():
    """Sample plan dictionary from Jules API."""
    return {
        "id": "plan123",
        "steps": [
            {
                "id": "step1",
                "title": "Step 1",
                "description": "First step",
                "index": 0,
            },
            {
                "id": "step2",
                "title": "Step 2",
                "description": "Second step",
                "index": 1,
            },
        ],
        "createTime": "2024-01-01T00:00:00Z",
    }
