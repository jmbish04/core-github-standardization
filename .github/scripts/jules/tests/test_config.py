"""
Configuration: test_config.py

"""

"""Tests for config module."""

from jules import config


"""
test_base_url — TODO: describe purpose.

Returns:
    TODO: describe return value
"""
def test_base_url():
    """Test BASE_URL constant."""
    assert config.BASE_URL == "https://jules.googleapis.com/v1alpha"


"""
test_default_timeout — TODO: describe purpose.

Returns:
    TODO: describe return value
"""
def test_default_timeout():
    """Test DEFAULT_TIMEOUT constant."""
    assert config.DEFAULT_TIMEOUT == 30
    assert isinstance(config.DEFAULT_TIMEOUT, int)


"""
test_default_poll_interval — TODO: describe purpose.

Returns:
    TODO: describe return value
"""
def test_default_poll_interval():
    """Test DEFAULT_POLL_INTERVAL constant."""
    assert config.DEFAULT_POLL_INTERVAL == 5.0
    assert isinstance(config.DEFAULT_POLL_INTERVAL, float)


"""
test_active_states — TODO: describe purpose.

Returns:
    TODO: describe return value
"""
def test_active_states():
    """Test ACTIVE_STATES set."""
    expected = {
        "QUEUED",
        "PLANNING",
        "AWAITING_PLAN_APPROVAL",
        "AWAITING_USER_FEEDBACK",
        "IN_PROGRESS",
        "PAUSED",
    }
    assert config.ACTIVE_STATES == expected


"""
test_terminal_states — TODO: describe purpose.

Returns:
    TODO: describe return value
"""
def test_terminal_states():
    """Test TERMINAL_STATES set."""
    expected = {"COMPLETED", "FAILED", "STATE_UNSPECIFIED"}
    assert config.TERMINAL_STATES == expected


"""
test_dedup_scan_pages — TODO: describe purpose.

Returns:
    TODO: describe return value
"""
def test_dedup_scan_pages():
    """Test DEDUP_SCAN_PAGES constant."""
    assert config.DEDUP_SCAN_PAGES == 3


"""
test_dedup_fingerprint_length — TODO: describe purpose.

Returns:
    TODO: describe return value
"""
def test_dedup_fingerprint_length():
    """Test DEDUP_FINGERPRINT_LENGTH constant."""
    assert config.DEDUP_FINGERPRINT_LENGTH == 16


"""
test_pagination_constants — TODO: describe purpose.

Returns:
    TODO: describe return value
"""
def test_pagination_constants():
    """Test pagination-related constants."""
    assert config.DEFAULT_PAGE_SIZE == 30
    assert config.MAX_PAGE_SIZE == 100
    assert config.MIN_PAGE_SIZE == 1


"""
test_activity_types — TODO: describe purpose.

Returns:
    TODO: describe return value
"""
def test_activity_types():
    """Test ACTIVITY_TYPES set."""
    expected = {
        "agentMessaged",
        "userMessaged",
        "planGenerated",
        "planApproved",
        "progressUpdated",
        "sessionCompleted",
        "sessionFailed",
    }
    assert config.ACTIVITY_TYPES == expected


"""
test_default_agent_skills_prompt — TODO: describe purpose.

Returns:
    TODO: describe return value
"""
def test_default_agent_skills_prompt():
    """Test DEFAULT_AGENT_SKILLS_PROMPT constant."""
    assert "Agent Skills" in config.DEFAULT_AGENT_SKILLS_PROMPT
    assert "agentskills.io" in config.DEFAULT_AGENT_SKILLS_PROMPT
