"""
automation_mode.py
------------------
Defines the AutomationMode enum for Jules session automation settings.
"""

from enum import Enum


class AutomationMode(str, Enum):
    """
    Automation mode for Jules sessions.

    Attributes:
        UNSPECIFIED: Default/unspecified automation mode
        AUTO_CREATE_PR: Automatically create a pull request when session completes
    """

    UNSPECIFIED = "AUTOMATION_MODE_UNSPECIFIED"
    AUTO_CREATE_PR = "AUTO_CREATE_PR"
