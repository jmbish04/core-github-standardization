"""
Data Classes Package
--------------------
Contains all data classes and enums used in the Jules client.

This package provides:
- Enums for automation modes and session states
- Model classes for API responses (Session, Activity, Plan, etc.)
- Result classes for operation outcomes
"""

from .enums.automation_mode import AutomationMode
from .enums.session_state import SessionState
from .models.activity import Activity
from .models.dedup_result import DedupResult
from .models.plan import Plan, PlanStep
from .models.pull_request import PullRequest
from .models.session import Session

__all__ = [
    "AutomationMode",
    "SessionState",
    "Activity",
    "DedupResult",
    "Plan",
    "PlanStep",
    "PullRequest",
    "Session",
]
