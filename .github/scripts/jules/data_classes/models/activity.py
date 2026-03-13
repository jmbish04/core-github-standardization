"""
activity.py
-----------
Defines the Activity data class for Jules session activity events.
"""

from dataclasses import dataclass, field
from typing import Dict, List

from ...config import ACTIVITY_TYPES


@dataclass
class Activity:
    """
    Represents an activity/event in a Jules session.

    Activities track what happens during a session, such as agent messages,
    plan generation, progress updates, and session completion.

    Attributes:
        name: Resource name of the activity
        id: Unique identifier for the activity
        description: Human-readable description of the activity
        create_time: ISO 8601 timestamp when activity occurred
        originator: Who/what created the activity (e.g., "agent", "user")
        activity_type: Type of activity (e.g., "planGenerated", "agentMessaged")
        payload: Type-specific data for the activity
        artifacts: List of artifacts produced by the activity
    """

    name: str
    id: str
    description: str
    create_time: str
    originator: str
    activity_type: str
    payload: Dict
    artifacts: List = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: Dict) -> "Activity":
        """
        Create an Activity instance from a dictionary.

        Args:
            d: Dictionary containing activity data from Jules API

        Returns:
            Activity instance
        """
        activity_type = ""
        payload: Dict = {}

        # Find which activity type is present in the response
        for key in ACTIVITY_TYPES:
            if key in d:
                activity_type = key
                payload = d[key]
                break

        return cls(
            name=d.get("name", ""),
            id=d.get("id", ""),
            description=d.get("description", ""),
            create_time=d.get("createTime", ""),
            originator=d.get("originator", ""),
            activity_type=activity_type,
            payload=payload,
            artifacts=d.get("artifacts", []),
        )
