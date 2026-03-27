"""
Jules Service Module
--------------------
Modular Python client and utilities for interacting with the Jules REST API.

This package provides:
- JulesClient: Full-featured REST API client with deduplication logic
- Helper utilities for common Jules operations in GitHub Actions

Environment Variables:
    JULES_API_KEY: Required API key for Jules authentication

Usage:
    from jules import JulesClient

    client = JulesClient()
    session = client.create_session(
        prompt="Generate agent skills",
        source_name="sources/github--owner--repo",
        starting_branch="main"
    )
"""

from .jules_client import (
    JulesClient,
    Session,
    Activity,
    Plan,
    PlanStep,
    PullRequest,
    DedupResult,
    AutomationMode,
    SessionState,
)

__all__ = [
    "JulesClient",
    "Session",
    "Activity",
    "Plan",
    "PlanStep",
    "PullRequest",
    "DedupResult",
    "AutomationMode",
    "SessionState",
]

__version__ = "1.0.0"
