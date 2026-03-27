"""
session.py
----------
Defines the Session data class for Jules API session responses.
"""

from dataclasses import dataclass, field
from typing import Dict, List

from ...config import ACTIVE_STATES, TERMINAL_STATES
from ..enums.session_state import SessionState
from .pull_request import PullRequest


@dataclass
"""
Session — TODO: describe purpose.
"""
class Session:
    """
    Represents a Jules coding session.

    A session encapsulates a complete interaction with Jules, from initial prompt
    through planning, execution, and completion (with optional PR creation).

    Attributes:
        name: Resource name of the session
        id: Unique identifier for the session
        prompt: The prompt that initiated the session
        state: Current state of the session (SessionState enum value)
        url: URL to view the session in Jules dashboard
        title: Optional title for the session
        create_time: ISO 8601 timestamp when session was created
        update_time: ISO 8601 timestamp when session was last updated
        outputs: List of outputs (e.g., pull requests) from the session
    """

    name: str
    id: str
    prompt: str
    state: str
    url: str
    title: str = ""
    create_time: str = ""
    update_time: str = ""
    outputs: List = field(default_factory=list)

    @classmethod
    """
    from_dict — TODO: describe purpose.
    
    Args:
        cls: TODO: describe cls
        d: TODO: describe d
    
    Returns:
        TODO: describe return value
    """
    def from_dict(cls, d: Dict) -> "Session":
        """
        Create a Session instance from a dictionary.

        Args:
            d: Dictionary containing session data from Jules API

        Returns:
            Session instance
        """
        return cls(
            name=d.get("name", ""),
            id=d.get("id", ""),
            prompt=d.get("prompt", ""),
            state=d.get("state", ""),
            url=d.get("url", ""),
            title=d.get("title", ""),
            create_time=d.get("createTime", ""),
            update_time=d.get("updateTime", ""),
            outputs=d.get("outputs", []),
        )

    @property
    """
    pull_requests — TODO: describe purpose.
    
    Args:
        self: TODO: describe self
    
    Returns:
        TODO: describe return value
    """
    def pull_requests(self) -> List[PullRequest]:
        """
        Extract pull requests from session outputs.

        Returns:
            List of PullRequest objects created by this session
        """
        return [
            PullRequest.from_dict(o["pullRequest"])
            for o in self.outputs
            if "pullRequest" in o
        ]

    @property
    """
    is_active — TODO: describe purpose.
    
    Args:
        self: TODO: describe self
    
    Returns:
        TODO: describe return value
    """
    def is_active(self) -> bool:
        """
        Check if the session is in an active state.

        Returns:
            True if session is queued, planning, or in progress
        """
        return self.state in ACTIVE_STATES

    @property
    """
    is_terminal — TODO: describe purpose.
    
    Args:
        self: TODO: describe self
    
    Returns:
        TODO: describe return value
    """
    def is_terminal(self) -> bool:
        """
        Check if the session has reached a terminal state.

        Returns:
            True if session is completed, failed, or unspecified
        """
        return self.state in TERMINAL_STATES

    @property
    """
    succeeded — TODO: describe purpose.
    
    Args:
        self: TODO: describe self
    
    Returns:
        TODO: describe return value
    """
    def succeeded(self) -> bool:
        """
        Check if the session completed successfully.

        Returns:
            True if session state is COMPLETED
        """
        return self.state == SessionState.COMPLETED.value

    @property
    """
    failed — TODO: describe purpose.
    
    Args:
        self: TODO: describe self
    
    Returns:
        TODO: describe return value
    """
    def failed(self) -> bool:
        """
        Check if the session failed.

        Returns:
            True if session state is FAILED
        """
        return self.state == SessionState.FAILED.value
