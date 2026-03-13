"""
session_state.py
----------------
Defines the SessionState enum for Jules session lifecycle states.
"""

from enum import Enum


class SessionState(str, Enum):
    """
    Possible states of a Jules session.

    Attributes:
        UNSPECIFIED: State is not specified
        QUEUED: Session is queued for processing
        PLANNING: Session is in planning phase
        AWAITING_PLAN_APPROVAL: Waiting for user to approve the plan
        AWAITING_USER_FEEDBACK: Waiting for user feedback
        IN_PROGRESS: Session is actively running
        PAUSED: Session is paused
        FAILED: Session has failed
        COMPLETED: Session has completed successfully
    """

    UNSPECIFIED = "STATE_UNSPECIFIED"
    QUEUED = "QUEUED"
    PLANNING = "PLANNING"
    AWAITING_PLAN_APPROVAL = "AWAITING_PLAN_APPROVAL"
    AWAITING_USER_FEEDBACK = "AWAITING_USER_FEEDBACK"
    IN_PROGRESS = "IN_PROGRESS"
    PAUSED = "PAUSED"
    FAILED = "FAILED"
    COMPLETED = "COMPLETED"
