"""Tests for utility functions."""

import pytest

from jules.data_classes import Activity, DedupResult, Plan, Session
from jules.utils import check_for_duplicate, log_activity, prompt_fingerprint


class TestPromptFingerprint:
    """Tests for prompt_fingerprint function."""

    def test_same_prompt_same_fingerprint(self):
        """Test that identical prompts produce same fingerprint."""
        prompt1 = "Test prompt"
        prompt2 = "Test prompt"
        assert prompt_fingerprint(prompt1) == prompt_fingerprint(prompt2)

    def test_whitespace_normalized(self):
        """Test that whitespace differences are normalized."""
        prompt1 = "Test   prompt"
        prompt2 = "Test prompt"
        assert prompt_fingerprint(prompt1) == prompt_fingerprint(prompt2)

    def test_case_insensitive(self):
        """Test that fingerprinting is case-insensitive."""
        prompt1 = "Test Prompt"
        prompt2 = "test prompt"
        assert prompt_fingerprint(prompt1) == prompt_fingerprint(prompt2)

    def test_different_prompts_different_fingerprints(self):
        """Test that different prompts produce different fingerprints."""
        prompt1 = "Test prompt 1"
        prompt2 = "Test prompt 2"
        assert prompt_fingerprint(prompt1) != prompt_fingerprint(prompt2)

    def test_fingerprint_length(self):
        """Test that fingerprint has correct length."""
        fp = prompt_fingerprint("Test prompt")
        assert len(fp) == 16


class TestCheckForDuplicate:
    """Tests for check_for_duplicate function."""

    def test_no_existing_sessions(self):
        """Test with no existing sessions."""
        result = check_for_duplicate(
            existing_sessions=[],
            source_name="sources/github--owner--repo",
            starting_branch="main",
            prompt="Test prompt",
        )
        assert result.is_duplicate is False
        assert result.existing_session is None

    def test_duplicate_found_active_session(self):
        """Test finding a duplicate active session."""
        session = Session(
            name="sessions/test123",
            id="test123",
            prompt="Test prompt",
            state="IN_PROGRESS",
            url="https://example.com/sessions/test123",
        )
        result = check_for_duplicate(
            existing_sessions=[session],
            source_name="sources/github--owner--repo",
            starting_branch="main",
            prompt="Test prompt",
            block_active_only=True,
        )
        assert result.is_duplicate is True
        assert result.existing_session.id == "test123"

    def test_no_duplicate_terminal_session_with_block_active_only(self):
        """Test that terminal sessions are not considered duplicates when block_active_only=True."""
        session = Session(
            name="sessions/test123",
            id="test123",
            prompt="Test prompt",
            state="COMPLETED",
            url="https://example.com/sessions/test123",
        )
        result = check_for_duplicate(
            existing_sessions=[session],
            source_name="sources/github--owner--repo",
            starting_branch="main",
            prompt="Test prompt",
            block_active_only=True,
        )
        assert result.is_duplicate is False

    def test_duplicate_terminal_session_without_block_active_only(self):
        """Test that terminal sessions are considered duplicates when block_active_only=False."""
        session = Session(
            name="sessions/test123",
            id="test123",
            prompt="Test prompt",
            state="COMPLETED",
            url="https://example.com/sessions/test123",
        )
        result = check_for_duplicate(
            existing_sessions=[session],
            source_name="sources/github--owner--repo",
            starting_branch="main",
            prompt="Test prompt",
            block_active_only=False,
        )
        assert result.is_duplicate is True

    def test_different_prompts_no_duplicate(self):
        """Test that different prompts don't match."""
        session = Session(
            name="sessions/test123",
            id="test123",
            prompt="Different prompt",
            state="IN_PROGRESS",
            url="https://example.com/sessions/test123",
        )
        result = check_for_duplicate(
            existing_sessions=[session],
            source_name="sources/github--owner--repo",
            starting_branch="main",
            prompt="Test prompt",
        )
        assert result.is_duplicate is False


class TestLogActivity:
    """Tests for log_activity function."""

    def test_log_plan_generated(self, sample_plan_dict):
        """Test logging a planGenerated activity."""
        activity = Activity(
            name="sessions/test/activities/act1",
            id="act1",
            description="Plan generated",
            create_time="2024-01-01T00:00:00Z",
            originator="agent",
            activity_type="planGenerated",
            payload={"plan": sample_plan_dict},
            artifacts=[],
        )

        logs = []
        log_activity(activity, logs.append)

        assert len(logs) == 3  # Plan header + 2 steps
        assert "Plan generated" in logs[0]
        assert "2 step(s)" in logs[0]
        assert "Step 1" in logs[1]
        assert "Step 2" in logs[2]

    def test_log_plan_approved(self):
        """Test logging a planApproved activity."""
        activity = Activity(
            name="sessions/test/activities/act1",
            id="act1",
            description="Plan approved",
            create_time="2024-01-01T00:00:00Z",
            originator="user",
            activity_type="planApproved",
            payload={"planId": "plan123"},
            artifacts=[],
        )

        logs = []
        log_activity(activity, logs.append)

        assert len(logs) == 1
        assert "Plan approved" in logs[0]
        assert "plan123" in logs[0]

    def test_log_progress_updated(self):
        """Test logging a progressUpdated activity."""
        activity = Activity(
            name="sessions/test/activities/act1",
            id="act1",
            description="Progress update",
            create_time="2024-01-01T00:00:00Z",
            originator="agent",
            activity_type="progressUpdated",
            payload={"title": "Creating files", "description": "Added config.py"},
            artifacts=[],
        )

        logs = []
        log_activity(activity, logs.append)

        assert len(logs) == 1
        assert "Creating files" in logs[0]
        assert "Added config.py" in logs[0]

    def test_log_agent_messaged(self):
        """Test logging an agentMessaged activity."""
        activity = Activity(
            name="sessions/test/activities/act1",
            id="act1",
            description="Agent message",
            create_time="2024-01-01T00:00:00Z",
            originator="agent",
            activity_type="agentMessaged",
            payload={"agentMessage": "Starting work"},
            artifacts=[],
        )

        logs = []
        log_activity(activity, logs.append)

        assert len(logs) == 1
        assert "Agent: Starting work" in logs[0]

    def test_log_session_completed(self):
        """Test logging a sessionCompleted activity."""
        activity = Activity(
            name="sessions/test/activities/act1",
            id="act1",
            description="Session completed",
            create_time="2024-01-01T00:00:00Z",
            originator="system",
            activity_type="sessionCompleted",
            payload={},
            artifacts=[],
        )

        logs = []
        log_activity(activity, logs.append)

        assert len(logs) == 1
        assert "Session completed" in logs[0]

    def test_log_session_failed_raises_error(self):
        """Test that sessionFailed raises RuntimeError."""
        activity = Activity(
            name="sessions/test/activities/act1",
            id="act1",
            description="Session failed",
            create_time="2024-01-01T00:00:00Z",
            originator="system",
            activity_type="sessionFailed",
            payload={"reason": "Test failure"},
            artifacts=[],
        )

        with pytest.raises(RuntimeError, match="Test failure"):
            log_activity(activity, print)
