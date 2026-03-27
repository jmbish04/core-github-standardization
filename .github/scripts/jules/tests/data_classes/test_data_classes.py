"""
Test suite: test_data_classes.py

"""

"""Tests for data classes."""

import pytest

from jules.data_classes import (
    Activity,
    AutomationMode,
    DedupResult,
    Plan,
    PlanStep,
    PullRequest,
    Session,
    SessionState,
)


"""
TestAutomationMode — TODO: describe purpose.
"""
class TestAutomationMode:
    """Tests for AutomationMode enum."""

    def test_values(self):
        """Test enum values."""
        assert AutomationMode.UNSPECIFIED.value == "AUTOMATION_MODE_UNSPECIFIED"
        assert AutomationMode.AUTO_CREATE_PR.value == "AUTO_CREATE_PR"


"""
TestSessionState — TODO: describe purpose.
"""
class TestSessionState:
    """Tests for SessionState enum."""

    def test_all_states(self):
        """Test all session state values."""
        assert SessionState.UNSPECIFIED.value == "STATE_UNSPECIFIED"
        assert SessionState.QUEUED.value == "QUEUED"
        assert SessionState.PLANNING.value == "PLANNING"
        assert SessionState.AWAITING_PLAN_APPROVAL.value == "AWAITING_PLAN_APPROVAL"
        assert SessionState.AWAITING_USER_FEEDBACK.value == "AWAITING_USER_FEEDBACK"
        assert SessionState.IN_PROGRESS.value == "IN_PROGRESS"
        assert SessionState.PAUSED.value == "PAUSED"
        assert SessionState.FAILED.value == "FAILED"
        assert SessionState.COMPLETED.value == "COMPLETED"


"""
TestPullRequest — TODO: describe purpose.
"""
class TestPullRequest:
    """Tests for PullRequest data class."""

    def test_from_dict(self, sample_pull_request_dict):
        """Test creating PullRequest from dict."""
        pr = PullRequest.from_dict(sample_pull_request_dict)
        assert pr.url == sample_pull_request_dict["url"]
        assert pr.title == sample_pull_request_dict["title"]
        assert pr.description == sample_pull_request_dict["description"]

    """
    test_from_dict_minimal — TODO: describe purpose.
    
    Args:
        self: TODO: describe self
    
    Returns:
        TODO: describe return value
    """
    def test_from_dict_minimal(self):
        """Test creating PullRequest with minimal data."""
        pr = PullRequest.from_dict({"url": "https://github.com/owner/repo/pull/1"})
        assert pr.url == "https://github.com/owner/repo/pull/1"
        assert pr.title == ""
        assert pr.description == ""


"""
TestPlanStep — TODO: describe purpose.
"""
class TestPlanStep:
    """Tests for PlanStep data class."""

    def test_from_dict(self):
        """Test creating PlanStep from dict."""
        data = {
            "id": "step1",
            "title": "Step 1",
            "description": "First step",
            "index": 0,
        }
        step = PlanStep.from_dict(data)
        assert step.id == "step1"
        assert step.title == "Step 1"
        assert step.description == "First step"
        assert step.index == 0


"""
TestPlan — TODO: describe purpose.
"""
class TestPlan:
    """Tests for Plan data class."""

    def test_from_dict(self, sample_plan_dict):
        """Test creating Plan from dict."""
        plan = Plan.from_dict(sample_plan_dict)
        assert plan.id == "plan123"
        assert len(plan.steps) == 2
        assert plan.steps[0].title == "Step 1"
        assert plan.steps[1].title == "Step 2"
        assert plan.create_time == "2024-01-01T00:00:00Z"


"""
TestActivity — TODO: describe purpose.
"""
class TestActivity:
    """Tests for Activity data class."""

    def test_from_dict(self, sample_activity_dict):
        """Test creating Activity from dict."""
        activity = Activity.from_dict(sample_activity_dict)
        assert activity.id == "act123"
        assert activity.name == "sessions/test123/activities/act123"
        assert activity.description == "Test activity"
        assert activity.originator == "agent"
        assert activity.activity_type == "agentMessaged"
        assert activity.payload == {"agentMessage": "Hello"}

    """
    test_from_dict_plan_generated — TODO: describe purpose.
    
    Args:
        self: TODO: describe self
    
    Returns:
        TODO: describe return value
    """
    def test_from_dict_plan_generated(self):
        """Test Activity with planGenerated type."""
        data = {
            "name": "sessions/test/activities/act1",
            "id": "act1",
            "description": "Plan generated",
            "createTime": "2024-01-01T00:00:00Z",
            "originator": "agent",
            "planGenerated": {"plan": {"id": "plan1", "steps": []}},
            "artifacts": [],
        }
        activity = Activity.from_dict(data)
        assert activity.activity_type == "planGenerated"
        assert "plan" in activity.payload


"""
TestSession — TODO: describe purpose.
"""
class TestSession:
    """Tests for Session data class."""

    def test_from_dict(self, sample_session_dict):
        """Test creating Session from dict."""
        session = Session.from_dict(sample_session_dict)
        assert session.id == "test123"
        assert session.name == "sessions/test123"
        assert session.prompt == "Test prompt"
        assert session.state == "QUEUED"
        assert session.url == "https://jules.example.com/sessions/test123"
        assert session.title == "Test Session"

    """
    test_pull_requests_property — TODO: describe purpose.
    
    Args:
        self: TODO: describe self
    
    Returns:
        TODO: describe return value
    """
    def test_pull_requests_property(self):
        """Test pull_requests property."""
        data = {
            "name": "sessions/test123",
            "id": "test123",
            "prompt": "Test",
            "state": "COMPLETED",
            "url": "https://example.com",
            "outputs": [
                {"pullRequest": {"url": "https://github.com/owner/repo/pull/1", "title": "PR 1"}},
                {"pullRequest": {"url": "https://github.com/owner/repo/pull/2", "title": "PR 2"}},
            ],
        }
        session = Session.from_dict(data)
        prs = session.pull_requests
        assert len(prs) == 2
        assert prs[0].url == "https://github.com/owner/repo/pull/1"
        assert prs[1].url == "https://github.com/owner/repo/pull/2"

    """
    test_is_active — TODO: describe purpose.
    
    Args:
        self: TODO: describe self
    
    Returns:
        TODO: describe return value
    """
    def test_is_active(self):
        """Test is_active property."""
        session = Session.from_dict({
            "name": "sessions/test",
            "id": "test",
            "prompt": "Test",
            "state": "IN_PROGRESS",
            "url": "https://example.com",
        })
        assert session.is_active is True

        session.state = "COMPLETED"
        assert session.is_active is False

    """
    test_is_terminal — TODO: describe purpose.
    
    Args:
        self: TODO: describe self
    
    Returns:
        TODO: describe return value
    """
    def test_is_terminal(self):
        """Test is_terminal property."""
        session = Session.from_dict({
            "name": "sessions/test",
            "id": "test",
            "prompt": "Test",
            "state": "COMPLETED",
            "url": "https://example.com",
        })
        assert session.is_terminal is True

        session.state = "IN_PROGRESS"
        assert session.is_terminal is False

    """
    test_succeeded — TODO: describe purpose.
    
    Args:
        self: TODO: describe self
    
    Returns:
        TODO: describe return value
    """
    def test_succeeded(self):
        """Test succeeded property."""
        session = Session.from_dict({
            "name": "sessions/test",
            "id": "test",
            "prompt": "Test",
            "state": "COMPLETED",
            "url": "https://example.com",
        })
        assert session.succeeded is True

        session.state = "FAILED"
        assert session.succeeded is False

    """
    test_failed — TODO: describe purpose.
    
    Args:
        self: TODO: describe self
    
    Returns:
        TODO: describe return value
    """
    def test_failed(self):
        """Test failed property."""
        session = Session.from_dict({
            "name": "sessions/test",
            "id": "test",
            "prompt": "Test",
            "state": "FAILED",
            "url": "https://example.com",
        })
        assert session.failed is True

        session.state = "COMPLETED"
        assert session.failed is False


"""
TestDedupResult — TODO: describe purpose.
"""
class TestDedupResult:
    """Tests for DedupResult data class."""

    def test_no_duplicate(self):
        """Test DedupResult with no duplicate."""
        result = DedupResult(is_duplicate=False, reason="No duplicate found")
        assert result.is_duplicate is False
        assert result.existing_session is None
        assert result.reason == "No duplicate found"

    """
    test_with_duplicate — TODO: describe purpose.
    
    Args:
        self: TODO: describe self
        sample_session_dict: TODO: describe sample_session_dict
    
    Returns:
        TODO: describe return value
    """
    def test_with_duplicate(self, sample_session_dict):
        """Test DedupResult with duplicate."""
        session = Session.from_dict(sample_session_dict)
        result = DedupResult(
            is_duplicate=True,
            existing_session=session,
            reason="Duplicate found",
        )
        assert result.is_duplicate is True
        assert result.existing_session is not None
        assert result.existing_session.id == "test123"
        assert result.reason == "Duplicate found"
