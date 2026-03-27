"""
config.py
---------
Configuration constants and values for the Jules client.

This module centralizes all configuration values, constants, and default settings
used throughout the Jules client package.
"""

from typing import Final

# ---------------------------------------------------------------------------
# API Configuration
# ---------------------------------------------------------------------------

BASE_URL: Final[str] = "https://jules.googleapis.com/v1alpha"
"""Base URL for the Jules REST API."""

DEFAULT_TIMEOUT: Final[int] = 30
"""Default timeout in seconds for HTTP requests."""

DEFAULT_POLL_INTERVAL: Final[float] = 5.0
"""Default interval in seconds between activity polling."""

# ---------------------------------------------------------------------------
# Session State Constants
# ---------------------------------------------------------------------------

ACTIVE_STATES: Final[set[str]] = {
    "QUEUED",
    "PLANNING",
    "AWAITING_PLAN_APPROVAL",
    "AWAITING_USER_FEEDBACK",
    "IN_PROGRESS",
    "PAUSED",
}
"""Sessions in these states are still 'alive' – block duplicate creation."""

TERMINAL_STATES: Final[set[str]] = {
    "COMPLETED",
    "FAILED",
    "STATE_UNSPECIFIED",
}
"""Sessions in these states are done – safe to create a new one."""

# ---------------------------------------------------------------------------
# Deduplication Configuration
# ---------------------------------------------------------------------------

DEDUP_SCAN_PAGES: Final[int] = 3
"""How many pages of sessions to scan when checking for duplicates (max 100 per page)."""

DEDUP_FINGERPRINT_LENGTH: Final[int] = 16
"""Length of the SHA-256 hex digest used for prompt fingerprinting."""

# ---------------------------------------------------------------------------
# Pagination Configuration
# ---------------------------------------------------------------------------

DEFAULT_PAGE_SIZE: Final[int] = 30
"""Default number of items to fetch per page."""

MAX_PAGE_SIZE: Final[int] = 100
"""Maximum number of items that can be fetched per page."""

MIN_PAGE_SIZE: Final[int] = 1
"""Minimum number of items that can be fetched per page."""

# ---------------------------------------------------------------------------
# Default Prompts
# ---------------------------------------------------------------------------

DEFAULT_AGENT_SKILLS_PROMPT: Final[str] = (
    "Analyze this repository and suggest Agent Skills to improve automation "
    "of common or complex tasks.\\n\\n"
    "Use the Agent Skills specification at https://agentskills.io/specification.md "
    "as the reference for formatting and structuring the skills.\\n\\n"
    "Tasks:\\n"
    "1. Review the repository structure, code, and existing workflows.\\n"
    "2. Identify 1–3 areas where an Agent Skill could be beneficial "
    "(e.g. code review, automated testing, boilerplate generation, "
    "or domain-specific formatting rules).\\n"
    "3. Create the corresponding Agent Skills configuration files "
    "(e.g. in a .jules/skills/ directory, per the specification).\\n"
    "4. Provide a brief explanation of what each skill does and why "
    "it is useful for this repository."
)
"""Default prompt for agent skills generation sessions."""

# ---------------------------------------------------------------------------
# Activity Types
# ---------------------------------------------------------------------------

ACTIVITY_TYPES: Final[set[str]] = {
    "agentMessaged",
    "userMessaged",
    "planGenerated",
    "planApproved",
    "progressUpdated",
    "sessionCompleted",
    "sessionFailed",
}
"""Valid activity types in the Jules API."""
