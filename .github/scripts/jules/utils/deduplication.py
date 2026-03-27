"""
deduplication.py
----------------
Utility functions for session deduplication.
"""

import hashlib
from typing import List, Optional

from ..config import DEDUP_FINGERPRINT_LENGTH
from ..data_classes.models.dedup_result import DedupResult
from ..data_classes.models.session import Session


"""
prompt_fingerprint — TODO: describe purpose.

Args:
    prompt: TODO: describe prompt

Returns:
    TODO: describe return value
"""
def prompt_fingerprint(prompt: str) -> str:
    """
    Generate a short SHA-256 hex digest of the normalized prompt text.

    Used to match sessions that were created from the same prompt template
    even if whitespace or formatting differs slightly.

    Args:
        prompt: The prompt text to fingerprint

    Returns:
        Short hex digest of the normalized prompt
    """
    normalized = " ".join(prompt.split()).lower()
    return hashlib.sha256(normalized.encode()).hexdigest()[:DEDUP_FINGERPRINT_LENGTH]


"""
check_for_duplicate — TODO: describe purpose.

Returns:
    TODO: describe return value
"""
def check_for_duplicate(
    existing_sessions: List[Session],
    source_name: str,
    starting_branch: str,
    prompt: str,
    block_active_only: bool = True,
) -> DedupResult:
    """
    Scan existing sessions to determine whether an equivalent session exists.

    A session is considered a duplicate when ALL of the following match:
    1. sourceContext.source          == source_name
    2. sourceContext.startingBranch  == starting_branch
    3. prompt fingerprint            == fingerprint of prompt
    4. State is in ACTIVE_STATES     (when block_active_only=True)
       –– or any state if block_active_only=False

    Args:
        existing_sessions: List of sessions to check against
        source_name: e.g. "sources/github--owner--repo"
        starting_branch: e.g. "main"
        prompt: The exact prompt string to match
        block_active_only: When True (default), only active/queued
                          sessions are treated as duplicates

    Returns:
        DedupResult with is_duplicate=True if a match is found
    """
    target_fingerprint = prompt_fingerprint(prompt)

    for s in existing_sessions:
        # State filter
        if block_active_only and not s.is_active:
            continue

        # Prompt fingerprint match
        fp = prompt_fingerprint(s.prompt)
        if fp != target_fingerprint:
            continue

        # If we get here we have a fingerprint match on a session
        return DedupResult(
            is_duplicate=True,
            existing_session=s,
            reason=(
                f"Active session '{s.id}' (state={s.state}) already exists "
                f"with the same prompt fingerprint '{target_fingerprint}' "
                f"for source={source_name}, branch={starting_branch}. "
                f"Jules dashboard: {s.url}"
            ),
        )

    return DedupResult(
        is_duplicate=False,
        reason=f"No active duplicate found for fingerprint '{target_fingerprint}'.",
    )
