"""
dedup_result.py
---------------
Defines the DedupResult data class for session deduplication results.
"""

from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .session import Session


@dataclass
"""
DedupResult — TODO: describe purpose.
"""
class DedupResult:
    """
    Result of a session deduplication check.

    Returned by duplicate-check logic to provide full context about whether
    a session already exists that matches the criteria.

    Attributes:
        is_duplicate: True if a duplicate session was found
        existing_session: The conflicting session, if one was found
        reason: Human-readable explanation of the result
    """

    is_duplicate: bool
    existing_session: Optional["Session"] = None
    reason: str = ""
