"""
Utils Package
-------------
Contains utility functions and helpers for the Jules client.
"""

from .deduplication import check_for_duplicate, prompt_fingerprint
from .logging import log_activity

__all__ = [
    "check_for_duplicate",
    "prompt_fingerprint",
    "log_activity",
]
