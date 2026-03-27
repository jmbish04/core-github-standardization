"""
sessions_api.py
---------------
API client for Jules sessions endpoints.
"""

import time
from typing import Callable, Dict, Generator, List, Optional

from ..config import (
    DEFAULT_AGENT_SKILLS_PROMPT,
    DEFAULT_POLL_INTERVAL,
    DEDUP_SCAN_PAGES,
)
from ..data_classes.enums.automation_mode import AutomationMode
from ..data_classes.enums.session_state import SessionState
from ..data_classes.models.activity import Activity
from ..data_classes.models.dedup_result import DedupResult
from ..data_classes.models.session import Session
from ..utils.deduplication import check_for_duplicate


"""
SessionsAPI — TODO: describe purpose.
"""
class SessionsAPI:
    """
    Client for interacting with Jules sessions.

    Attributes:
        _get: HTTP GET function from parent client
        _post: HTTP POST function from parent client
        _activities_api: ActivitiesAPI instance for activity operations
    """

    def __init__(
        self,
        get_func: Callable[[str, Optional[Dict]], Dict],
        post_func: Callable[[str, Optional[Dict]], Dict],
        activities_api: "ActivitiesAPI",
    ):
        """
        Initialize the SessionsAPI.

        Args:
            get_func: HTTP GET function from the parent JulesClient
            post_func: HTTP POST function from the parent JulesClient
            activities_api: ActivitiesAPI instance for activity operations
        """
        self._get = get_func
        self._post = post_func
        self._activities_api = activities_api

    """
    create_session — TODO: describe purpose.
    
    Returns:
        TODO: describe return value
    """
    def create_session(
        self,
        prompt: str,
        source_name: str,
        starting_branch: str = "main",
        title: Optional[str] = None,
        require_plan_approval: bool = False,
        automation_mode: AutomationMode = AutomationMode.AUTO_CREATE_PR,
    ) -> Session:
        """
        Create a new Jules session (raw, no dedup check).

        Args:
            prompt: The prompt to initiate the session
            source_name: Resource name of the source (e.g., "sources/github--owner--repo")
            starting_branch: Branch to work from (default: "main")
            title: Optional title for the session
            require_plan_approval: Whether to require manual plan approval
            automation_mode: Automation mode for the session

        Returns:
            Session instance
        """
        body: Dict = {
            "prompt": prompt,
            "sourceContext": {
                "source": source_name,
                "githubRepoContext": {"startingBranch": starting_branch},
            },
            "requirePlanApproval": require_plan_approval,
            "automationMode": automation_mode.value,
        }
        if title:
            body["title"] = title
        return Session.from_dict(self._post("sessions", body))

    """
    get_session — TODO: describe purpose.
    
    Args:
        self: TODO: describe self
        session_id: TODO: describe session_id
    
    Returns:
        TODO: describe return value
    """
    def get_session(self, session_id: str) -> Session:
        """
        Get a session by bare ID or full resource name.

        Args:
            session_id: Session ID or full resource name

        Returns:
            Session instance
        """
        name = (
            session_id
            if session_id.startswith("sessions/")
            else f"sessions/{session_id}"
        )
        return Session.from_dict(self._get(name, None))

    """
    list_sessions — TODO: describe purpose.
    
    Returns:
        TODO: describe return value
    """
    def list_sessions(
        self, page_size: int = 30, page_token: Optional[str] = None
    ) -> Dict:
        """
        List sessions with pagination.

        Args:
            page_size: Number of sessions per page (1-100)
            page_token: Token for fetching the next page

        Returns:
            Dictionary with "sessions" list and "nextPageToken"
        """
        params: Dict = {"pageSize": min(max(page_size, 1), 100)}
        if page_token:
            params["pageToken"] = page_token
        raw = self._get("sessions", params)
        return {
            "sessions": [Session.from_dict(s) for s in raw.get("sessions", [])],
            "nextPageToken": raw.get("nextPageToken", ""),
        }

    """
    list_all_sessions — TODO: describe purpose.
    
    Args:
        self: TODO: describe self
        max_pages: TODO: describe max_pages
    
    Returns:
        TODO: describe return value
    """
    def list_all_sessions(self, max_pages: int = DEDUP_SCAN_PAGES) -> List[Session]:
        """
        Fetch up to max_pages pages of sessions and return them as a flat list.

        Used by the deduplication scan.

        Args:
            max_pages: Maximum number of pages to fetch

        Returns:
            List of Session instances
        """
        sessions: List[Session] = []
        page_token: Optional[str] = None
        for _ in range(max_pages):
            result = self.list_sessions(page_size=100, page_token=page_token)
            sessions.extend(result["sessions"])
            page_token = result.get("nextPageToken") or None
            if not page_token:
                break
        return sessions

    """
    approve_plan — TODO: describe purpose.
    
    Args:
        self: TODO: describe self
        session_id: TODO: describe session_id
    
    Returns:
        TODO: describe return value
    """
    def approve_plan(self, session_id: str) -> None:
        """
        Approve the pending plan in a session.

        Args:
            session_id: Session ID or full resource name
        """
        name = (
            session_id
            if session_id.startswith("sessions/")
            else f"sessions/{session_id}"
        )
        self._post(f"{name}:approvePlan", None)

    """
    send_message — TODO: describe purpose.
    
    Args:
        self: TODO: describe self
        session_id: TODO: describe session_id
        prompt: TODO: describe prompt
    
    Returns:
        TODO: describe return value
    """
    def send_message(self, session_id: str, prompt: str) -> None:
        """
        Send a follow-up message to an active session.

        Args:
            session_id: Session ID or full resource name
            prompt: The message to send
        """
        name = (
            session_id
            if session_id.startswith("sessions/")
            else f"sessions/{session_id}"
        )
        self._post(f"{name}:sendMessage", {"prompt": prompt})

    """
    check_for_duplicate — TODO: describe purpose.
    
    Returns:
        TODO: describe return value
    """
    def check_for_duplicate(
        self,
        source_name: str,
        starting_branch: str,
        prompt: str,
        block_active_only: bool = True,
    ) -> DedupResult:
        """
        Scan existing sessions to determine whether an equivalent session exists.

        Args:
            source_name: e.g. "sources/github--owner--repo"
            starting_branch: e.g. "main"
            prompt: The exact prompt string to match
            block_active_only: When True (default), only active/queued
                              sessions are treated as duplicates

        Returns:
            DedupResult instance
        """
        existing_sessions = self.list_all_sessions()
        return check_for_duplicate(
            existing_sessions=existing_sessions,
            source_name=source_name,
            starting_branch=starting_branch,
            prompt=prompt,
            block_active_only=block_active_only,
        )

    """
    create_session_safe — TODO: describe purpose.
    
    Returns:
        TODO: describe return value
    """
    def create_session_safe(
        self,
        prompt: str,
        source_name: str,
        starting_branch: str = "main",
        title: Optional[str] = None,
        require_plan_approval: bool = False,
        automation_mode: AutomationMode = AutomationMode.AUTO_CREATE_PR,
        block_active_only: bool = True,
        log_fn: Optional[Callable[[str], None]] = None,
    ) -> tuple[Session, bool]:
        """
        Dedup-aware wrapper around create_session.

        Checks for an existing active session with the same prompt fingerprint
        before creating a new one.

        Args:
            prompt: The prompt to initiate the session
            source_name: Resource name of the source
            starting_branch: Branch to work from (default: "main")
            title: Optional title for the session
            require_plan_approval: Whether to require manual plan approval
            automation_mode: Automation mode for the session
            block_active_only: See check_for_duplicate
            log_fn: Logging callback (default: print)

        Returns:
            Tuple of (session, was_existing) - if a duplicate was found,
            the existing session is returned and was_existing is True
        """
        log = log_fn or print

        dedup = self.check_for_duplicate(
            source_name=source_name,
            starting_branch=starting_branch,
            prompt=prompt,
            block_active_only=block_active_only,
        )

        if dedup.is_duplicate and dedup.existing_session is not None:
            log(f"[Jules][dedup] Skipping — duplicate detected: {dedup.reason}")
            return dedup.existing_session, True

        log(f"[Jules][dedup] {dedup.reason}")
        session = self.create_session(
            prompt=prompt,
            source_name=source_name,
            starting_branch=starting_branch,
            title=title,
            require_plan_approval=require_plan_approval,
            automation_mode=automation_mode,
        )
        return session, False

    """
    run_agent_skills_session — TODO: describe purpose.
    
    Returns:
        TODO: describe return value
    """
    def run_agent_skills_session(
        self,
        source_name: str,
        starting_branch: str = "main",
        prompt: Optional[str] = None,
        require_plan_approval: bool = False,
        poll_interval: float = DEFAULT_POLL_INTERVAL,
        log_fn: Optional[Callable[[str], None]] = None,
        skip_if_active: bool = True,
        skip_if_completed: bool = True,
    ) -> Optional[str]:
        """
        End-to-end helper for the Jules GitHub Action.

        Creates (or reuses) a session that analyses the repo, generates Agent
        Skills configuration files, and opens a PR.

        Args:
            source_name: Resource name of the source
            starting_branch: Branch Jules should work from
            prompt: Override the default Agent Skills prompt
            require_plan_approval: Pause before Jules starts coding
            poll_interval: Seconds between activity polls
            log_fn: Callable(str) for status messages
            skip_if_active: Block duplicate when an active session exists
            skip_if_completed: Also block when a completed session exists

        Returns:
            PR URL string if a pull request was created/found, else None

        Raises:
            RuntimeError: if the Jules session ends in FAILED state
        """
        from ..utils.logging import log_activity

        log = log_fn or print
        effective_prompt = prompt or DEFAULT_AGENT_SKILLS_PROMPT

        # Deduplication check
        block_active_only = not skip_if_completed
        dedup = self.check_for_duplicate(
            source_name=source_name,
            starting_branch=starting_branch,
            prompt=effective_prompt,
            block_active_only=block_active_only,
        )

        if dedup.is_duplicate and dedup.existing_session is not None:
            existing = dedup.existing_session
            if existing.is_active and skip_if_active:
                log(
                    f"[Jules][dedup] ⚠ Duplicate suppressed — session '{existing.id}' "
                    f"is already {existing.state}. "
                    f"Attaching to existing session instead of creating a new one."
                )
                session = existing
            elif existing.succeeded and skip_if_completed:
                prs = existing.pull_requests
                pr_url = prs[0].url if prs else None
                log(
                    f"[Jules][dedup] ✓ Duplicate suppressed — identical session "
                    f"'{existing.id}' already COMPLETED. "
                    + (f"PR: {pr_url}" if pr_url else "No PR was generated.")
                )
                return pr_url
            else:
                log(
                    f"[Jules][dedup] Previous session '{existing.id}' is in state "
                    f"'{existing.state}' — creating a fresh session."
                )
                session = self.create_session(
                    prompt=effective_prompt,
                    source_name=source_name,
                    starting_branch=starting_branch,
                    title="Generate Agent Skills",
                    require_plan_approval=require_plan_approval,
                    automation_mode=AutomationMode.AUTO_CREATE_PR,
                )
        else:
            log(f"[Jules] Creating session for source={source_name}, branch={starting_branch}")
            session = self.create_session(
                prompt=effective_prompt,
                source_name=source_name,
                starting_branch=starting_branch,
                title="Generate Agent Skills",
                require_plan_approval=require_plan_approval,
                automation_mode=AutomationMode.AUTO_CREATE_PR,
            )

        log(f"[Jules] Session active  →  id={session.id}  state={session.state}  url={session.url}")

        if not session.is_terminal:
            for activity in self._activities_api.stream_activities(
                session.id,
                poll_interval=poll_interval,
                auto_approve_plans=(not require_plan_approval),
            ):
                log_activity(activity, log)

        final = self.get_session(session.id)
        if final.failed:
            raise RuntimeError(f"Jules session '{final.id}' ended in FAILED state.")

        prs = final.pull_requests
        if prs:
            pr_url = prs[0].url
            log(f"[Jules] ✓ Pull Request: {pr_url}")
            return pr_url

        log("[Jules] Session finished — no pull request was generated.")
        return None
