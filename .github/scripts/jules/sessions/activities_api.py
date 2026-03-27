"""
activities_api.py
-----------------
API client for Jules activities endpoints.
"""

import time
from typing import Callable, Dict, Generator, Optional, Set

from ..config import DEFAULT_POLL_INTERVAL
from ..data_classes.enums.session_state import SessionState
from ..data_classes.models.activity import Activity


"""
ActivitiesAPI — TODO: describe purpose.
"""
class ActivitiesAPI:
    """
    Client for interacting with Jules activities.

    Attributes:
        _get: HTTP GET function from parent client
        _post: HTTP POST function from parent client
        _get_session_func: Function to get a session (to avoid circular dependency)
    """

    def __init__(
        self,
        get_func: Callable[[str, Optional[Dict]], Dict],
        post_func: Callable[[str, Optional[Dict]], Dict],
    ):
        """
        Initialize the ActivitiesAPI.

        Args:
            get_func: HTTP GET function from the parent JulesClient
            post_func: HTTP POST function from the parent JulesClient
        """
        self._get = get_func
        self._post = post_func
        self._get_session_func: Optional[Callable[[str], "Session"]] = None

    """
    set_get_session_func — TODO: describe purpose.
    
    Args:
        self: TODO: describe self
        func: TODO: describe func
        "Session"]: TODO: describe "Session"]
    
    Returns:
        TODO: describe return value
    """
    def set_get_session_func(self, func: Callable[[str], "Session"]) -> None:
        """
        Set the function to get a session.

        This is called after initialization to avoid circular dependencies.

        Args:
            func: Function that takes session_id and returns Session
        """
        self._get_session_func = func

    """
    get_activity — TODO: describe purpose.
    
    Args:
        self: TODO: describe self
        session_id: TODO: describe session_id
        activity_id: TODO: describe activity_id
    
    Returns:
        TODO: describe return value
    """
    def get_activity(self, session_id: str, activity_id: str) -> Activity:
        """
        Get a specific activity from a session.

        Args:
            session_id: Session ID or full resource name
            activity_id: Activity ID

        Returns:
            Activity instance
        """
        name = (
            session_id
            if session_id.startswith("sessions/")
            else f"sessions/{session_id}"
        )
        return Activity.from_dict(self._get(f"{name}/activities/{activity_id}", None))

    """
    list_activities — TODO: describe purpose.
    
    Returns:
        TODO: describe return value
    """
    def list_activities(
        self,
        session_id: str,
        page_size: int = 50,
        page_token: Optional[str] = None,
    ) -> Dict:
        """
        List activities for a session with pagination.

        Args:
            session_id: Session ID or full resource name
            page_size: Number of activities per page (1-100)
            page_token: Token for fetching the next page

        Returns:
            Dictionary with "activities" list and "nextPageToken"
        """
        name = (
            session_id
            if session_id.startswith("sessions/")
            else f"sessions/{session_id}"
        )
        params: Dict = {"pageSize": min(max(page_size, 1), 100)}
        if page_token:
            params["pageToken"] = page_token
        raw = self._get(f"{name}/activities", params)
        return {
            "activities": [Activity.from_dict(a) for a in raw.get("activities", [])],
            "nextPageToken": raw.get("nextPageToken", ""),
        }

    """
    stream_activities — TODO: describe purpose.
    
    Returns:
        TODO: describe return value
    """
    def stream_activities(
        self,
        session_id: str,
        poll_interval: float = DEFAULT_POLL_INTERVAL,
        auto_approve_plans: bool = True,
    ) -> Generator[Activity, None, None]:
        """
        Poll the activities list, yielding each new Activity as it appears.

        Continues until the session reaches a terminal state.

        Args:
            session_id: Session ID or full resource name
            poll_interval: Seconds to wait between polls
            auto_approve_plans: Whether to automatically approve generated plans

        Yields:
            Activity instances as they appear
        """
        if self._get_session_func is None:
            raise RuntimeError("get_session_func not set on ActivitiesAPI")

        seen_ids: Set[str] = set()
        page_token: Optional[str] = None

        while True:
            result = self.list_activities(session_id, page_token=page_token)
            for activity in result["activities"]:
                if activity.id not in seen_ids:
                    seen_ids.add(activity.id)
                    yield activity

                    if auto_approve_plans and activity.activity_type == "planGenerated":
                        current = self._get_session_func(session_id)
                        if current.state == SessionState.AWAITING_PLAN_APPROVAL.value:
                            # Approve the plan via SessionsAPI
                            name = (
                                session_id
                                if session_id.startswith("sessions/")
                                else f"sessions/{session_id}"
                            )
                            self._post(f"{name}:approvePlan", None)

            page_token = result.get("nextPageToken") or None
            current = self._get_session_func(session_id)
            if current.is_terminal:
                break

            time.sleep(poll_interval)
