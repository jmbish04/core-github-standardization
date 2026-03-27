"""
pull_request.py
---------------
Defines the PullRequest data class for Jules API pull request responses.
"""

from dataclasses import dataclass
from typing import Dict


@dataclass
"""
PullRequest — TODO: describe purpose.
"""
class PullRequest:
    """
    Represents a GitHub pull request created by Jules.

    Attributes:
        url: URL of the pull request
        title: Title of the pull request
        description: Description/body of the pull request
    """

    url: str
    title: str = ""
    description: str = ""

    @classmethod
    """
    from_dict — TODO: describe purpose.
    
    Args:
        cls: TODO: describe cls
        d: TODO: describe d
    
    Returns:
        TODO: describe return value
    """
    def from_dict(cls, d: Dict) -> "PullRequest":
        """
        Create a PullRequest instance from a dictionary.

        Args:
            d: Dictionary containing pull request data from Jules API

        Returns:
            PullRequest instance
        """
        return cls(
            url=d.get("url", ""),
            title=d.get("title", ""),
            description=d.get("description", ""),
        )
