"""
jules_client.py
---------------
Python client for the Jules REST API (v1alpha).
Designed to be used inside a Jules GitHub Action to generate Agent Skills.
Includes deduplication logic to prevent multiple Action runs from creating
redundant sessions for the same repo/branch/task combination.
Environment:
    JULES_API_KEY  – required Google API key with Jules API access
"""
import hashlib
import logging
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Generator, Optional
import requests
logger = logging.getLogger(__name__)
# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
BASE_URL = "https://jules.googleapis.com/v1alpha"
DEFAULT_POLL_INTERVAL = 5
# Sessions in these states are still "alive" – block duplicate creation
ACTIVE_STATES = {
    "QUEUED",
    "PLANNING",
    "AWAITING_PLAN_APPROVAL",
    "AWAITING_USER_FEEDBACK",
    "IN_PROGRESS",
    "PAUSED",
}
# Sessions in these states are done – safe to create a new one
TERMINAL_STATES = {"COMPLETED", "FAILED", "STATE_UNSPECIFIED"}
# How many sessions to scan when checking for duplicates (max 100 per page)
DEDUP_SCAN_PAGES = 3
# ---------------------------------------------------------------------------
# Enums & dataclasses
# ---------------------------------------------------------------------------
class AutomationMode(str, Enum):
    UNSPECIFIED = "AUTOMATION_MODE_UNSPECIFIED"
    AUTO_CREATE_PR = "AUTO_CREATE_PR"
"""
SessionState — TODO: describe purpose.

Args:
    str: TODO: describe str
    Enum: TODO: describe Enum
"""
class SessionState(str, Enum):
    UNSPECIFIED = "STATE_UNSPECIFIED"
    QUEUED = "QUEUED"
    PLANNING = "PLANNING"
    AWAITING_PLAN_APPROVAL = "AWAITING_PLAN_APPROVAL"
    AWAITING_USER_FEEDBACK = "AWAITING_USER_FEEDBACK"
    IN_PROGRESS = "IN_PROGRESS"
    PAUSED = "PAUSED"
    FAILED = "FAILED"
    COMPLETED = "COMPLETED"
@dataclass
"""
PullRequest — TODO: describe purpose.
"""
class PullRequest:
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
    def from_dict(cls, d: dict) -> "PullRequest":
        return cls(
            url=d.get("url", ""),
            title=d.get("title", ""),
            description=d.get("description", ""),
        )
@dataclass
"""
PlanStep — TODO: describe purpose.
"""
class PlanStep:
    id: str
    title: str
    description: str
    index: int
    @classmethod
    """
    from_dict — TODO: describe purpose.
    
    Args:
        cls: TODO: describe cls
        d: TODO: describe d
    
    Returns:
        TODO: describe return value
    """
    def from_dict(cls, d: dict) -> "PlanStep":
        return cls(
            id=d.get("id", ""),
            title=d.get("title", ""),
            description=d.get("description", ""),
            index=d.get("index", 0),
        )
@dataclass
"""
Plan — TODO: describe purpose.
"""
class Plan:
    id: str
    steps: list[PlanStep] = field(default_factory=list)
    create_time: str = ""
    @classmethod
    """
    from_dict — TODO: describe purpose.
    
    Args:
        cls: TODO: describe cls
        d: TODO: describe d
    
    Returns:
        TODO: describe return value
    """
    def from_dict(cls, d: dict) -> "Plan":
        return cls(
            id=d.get("id", ""),
            steps=[PlanStep.from_dict(s) for s in d.get("steps", [])],
            create_time=d.get("createTime", ""),
        )
@dataclass
"""
Activity — TODO: describe purpose.
"""
class Activity:
    name: str
    id: str
    description: str
    create_time: str
    originator: str
    activity_type: str
    payload: dict
    artifacts: list = field(default_factory=list)
    @classmethod
    """
    from_dict — TODO: describe purpose.
    
    Args:
        cls: TODO: describe cls
        d: TODO: describe d
    
    Returns:
        TODO: describe return value
    """
    def from_dict(cls, d: dict) -> "Activity":
        activity_type = ""
        payload: dict = {}
        for key in (
            "agentMessaged",
            "userMessaged",
            "planGenerated",
            "planApproved",
            "progressUpdated",
            "sessionCompleted",
            "sessionFailed",
        ):
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
@dataclass
"""
Session — TODO: describe purpose.
"""
class Session:
    name: str
    id: str
    prompt: str
    state: str
    url: str
    title: str = ""
    create_time: str = ""
    update_time: str = ""
    outputs: list = field(default_factory=list)
    @classmethod
    """
    from_dict — TODO: describe purpose.
    
    Args:
        cls: TODO: describe cls
        d: TODO: describe d
    
    Returns:
        TODO: describe return value
    """
    def from_dict(cls, d: dict) -> "Session":
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
    def pull_requests(self) -> list[PullRequest]:
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
        return self.state == SessionState.COMPLETED
    @property
    """
    failed — TODO: describe purpose.
    
    Args:
        self: TODO: describe self
    
    Returns:
        TODO: describe return value
    """
    def failed(self) -> bool:
        return self.state == SessionState.FAILED
# ---------------------------------------------------------------------------
# Deduplication result
# ---------------------------------------------------------------------------
@dataclass
"""
DedupResult — TODO: describe purpose.
"""
class DedupResult:
    """Returned by the duplicate-check logic so callers get full context."""
    is_duplicate: bool
    # The conflicting session, if one was found
    existing_session: Optional[Session] = None
    # Human-readable explanation of why this was (or wasn't) a duplicate
    reason: str = ""
# ---------------------------------------------------------------------------
# Main client
# ---------------------------------------------------------------------------
class JulesClient:
    """
    Full-coverage Python client for the Jules REST API (v1alpha).
    Includes deduplication logic that scans existing sessions before creating
    a new one, preventing the pile-up shown when GitHub Actions fire repeatedly.
    Quick path for GitHub Actions / Agent Skills generation:
        client = JulesClient()
        pr_url = client.run_agent_skills_session(
            source_name="sources/github--owner--repo",
            starting_branch="main",
        )
    """
    def __init__(self, api_key: Optional[str] = None, timeout: int = 30):
        self.api_key = api_key or os.environ.get("JULES_API_KEY")
        if not self.api_key:
            raise EnvironmentError(
                "Jules API key not found. "
                "Set JULES_API_KEY env var or pass api_key= to JulesClient()."
            )
        self.timeout = timeout
        self._session = requests.Session()
        self._session.headers.update({"Content-Type": "application/json"})
    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _url(self, path: str) -> str:
        return f"{BASE_URL}/{path.lstrip('/')}"
    """
    _params — TODO: describe purpose.
    
    Args:
        self: TODO: describe self
        extra: TODO: describe extra
    
    Returns:
        TODO: describe return value
    """
    def _params(self, extra: Optional[dict] = None) -> dict:
        p = {"key": self.api_key}
        if extra:
            p.update(extra)
        return p
    """
    _get — TODO: describe purpose.
    
    Args:
        self: TODO: describe self
        path: TODO: describe path
        params: TODO: describe params
    
    Returns:
        TODO: describe return value
    """
    def _get(self, path: str, params: Optional[dict] = None) -> dict:
        resp = self._session.get(
            self._url(path), params=self._params(params), timeout=self.timeout
        )
        resp.raise_for_status()
        return resp.json()
    """
    _post — TODO: describe purpose.
    
    Args:
        self: TODO: describe self
        path: TODO: describe path
        body: TODO: describe body
    
    Returns:
        TODO: describe return value
    """
    def _post(self, path: str, body: Optional[dict] = None) -> dict:
        resp = self._session.post(
            self._url(path), params=self._params(), json=body or {}, timeout=self.timeout
        )
        resp.raise_for_status()
        try:
            return resp.json() if resp.content else {}
        except ValueError:
            return {}
    # ------------------------------------------------------------------
    # Sources API
    # ------------------------------------------------------------------
    def list_sources(self) -> list[dict]:
        """Lists all sources (GitHub repos) connected to Jules."""
        return self._get("sources").get("sources", [])
    """
    get_source — TODO: describe purpose.
    
    Args:
        self: TODO: describe self
        source_name: TODO: describe source_name
    
    Returns:
        TODO: describe return value
    """
    def get_source(self, source_name: str) -> dict:
        """Gets a single source by resource name, e.g. ``sources/github--owner--repo``."""
        return self._get(source_name)
    """
    find_source_for_repo — TODO: describe purpose.
    
    Args:
        self: TODO: describe self
        owner: TODO: describe owner
        repo: TODO: describe repo
    
    Returns:
        TODO: describe return value
    """
    def find_source_for_repo(self, owner: str, repo: str) -> Optional[dict]:
        """
        Scans all sources and returns the one matching ``owner/repo``.
        Returns ``None`` if not found.
        """
        for source in self.list_sources():
            gh = source.get("githubRepo", {})
            if (
                gh.get("owner", "").lower() == owner.lower()
                and gh.get("repo", "").lower() == repo.lower()
            ):
                return source
        return None
    # ------------------------------------------------------------------
    # Sessions API
    # ------------------------------------------------------------------
    def create_session(
        self,
        prompt: str,
        source_name: str,
        starting_branch: str = "main",
        title: Optional[str] = None,
        require_plan_approval: bool = False,
        automation_mode: AutomationMode = AutomationMode.AUTO_CREATE_PR,
    ) -> Session:
        """Creates a new Jules session (raw, no dedup check)."""
        body: dict = {
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
        """Gets a session by bare ID or full resource name."""
        name = (
            session_id
            if session_id.startswith("sessions/")
            else f"sessions/{session_id}"
        )
        return Session.from_dict(self._get(name))
    """
    list_sessions — TODO: describe purpose.
    
    Returns:
        TODO: describe return value
    """
    def list_sessions(
        self, page_size: int = 30, page_token: Optional[str] = None
    ) -> dict:
        """
        Lists sessions.
        Returns:
            ``{"sessions": [Session, ...], "nextPageToken": str}``
        """
        params: dict = {"pageSize": min(max(page_size, 1), 100)}
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
    def list_all_sessions(self, max_pages: int = DEDUP_SCAN_PAGES) -> list[Session]:
        """
        Fetches up to ``max_pages`` pages of sessions and returns them as a
        flat list.  Used by the deduplication scan.
        """
        sessions: list[Session] = []
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
        """Approves the pending plan in a session."""
        name = (
            session_id
            if session_id.startswith("sessions/")
            else f"sessions/{session_id}"
        )
        self._post(f"{name}:approvePlan")
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
        """Sends a follow-up message to an active session."""
        name = (
            session_id
            if session_id.startswith("sessions/")
            else f"sessions/{session_id}"
        )
        self._post(f"{name}:sendMessage", {"prompt": prompt})
    # ------------------------------------------------------------------
    # Activities API
    # ------------------------------------------------------------------
    def get_activity(self, session_id: str, activity_id: str) -> Activity:
        name = (
            session_id
            if session_id.startswith("sessions/")
            else f"sessions/{session_id}"
        )
        return Activity.from_dict(self._get(f"{name}/activities/{activity_id}"))
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
    ) -> dict:
        name = (
            session_id
            if session_id.startswith("sessions/")
            else f"sessions/{session_id}"
        )
        params: dict = {"pageSize": min(max(page_size, 1), 100)}
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
        Polls the activities list, yielding each *new* Activity as it appears,
        until the session reaches a terminal state.
        """
        seen_ids: set[str] = set()
        page_token: Optional[str] = None
        while True:
            result = self.list_activities(session_id, page_token=page_token)
            for activity in result["activities"]:
                if activity.id not in seen_ids:
                    seen_ids.add(activity.id)
                    yield activity
                    if auto_approve_plans and activity.activity_type == "planGenerated":
                        current = self.get_session(session_id)
                        if current.state == SessionState.AWAITING_PLAN_APPROVAL:
                            logger.info("Auto-approving plan for session %s", session_id)
                            self.approve_plan(session_id)
            page_token = result.get("nextPageToken") or None
            current = self.get_session(session_id)
            if current.is_terminal:
                break
            time.sleep(poll_interval)
    # ------------------------------------------------------------------
    # Deduplication logic
    # ------------------------------------------------------------------
    @staticmethod
    """
    _prompt_fingerprint — TODO: describe purpose.
    
    Args:
        prompt: TODO: describe prompt
    
    Returns:
        TODO: describe return value
    """
    def _prompt_fingerprint(prompt: str) -> str:
        """
        Returns a short SHA-256 hex digest of the normalised prompt text.
        Used to match sessions that were created from the same prompt template
        even if whitespace or formatting differs slightly.
        """
        normalised = " ".join(prompt.split()).lower()
        return hashlib.sha256(normalised.encode()).hexdigest()[:16]
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
        *,
        block_active_only: bool = True,
    ) -> DedupResult:
        """
        Scans existing sessions to determine whether an equivalent session is
        already running (or recently completed).
        A session is considered a duplicate when ALL of the following match:
        1. ``sourceContext.source``          == ``source_name``
        2. ``sourceContext.startingBranch``  == ``starting_branch``
        3. prompt fingerprint                == fingerprint of ``prompt``
        4. State is in ``ACTIVE_STATES``     (when ``block_active_only=True``)
           –– or any state if ``block_active_only=False``
        Args:
            source_name:       e.g. ``"sources/github--owner--repo"``
            starting_branch:   e.g. ``"main"``
            prompt:            The exact prompt string you intend to send.
            block_active_only: When ``True`` (default), only active/queued
                               sessions are treated as duplicates.  Completed
                               or failed sessions are ignored so re-runs after
                               a failure are always allowed.
        Returns:
            :class:`DedupResult`
        """
        target_fingerprint = self._prompt_fingerprint(prompt)
        existing_sessions = self.list_all_sessions()
        for s in existing_sessions:
            # State filter
            if block_active_only and not s.is_active:
                continue
            # Source match — the API embeds source in the prompt field indirectly,
            # so we rely on the title/prompt heuristic plus fingerprint.
            # The sourceContext is not echoed back in list responses, so we
            # use the prompt fingerprint as the primary dedup key and the
            # session title as a secondary signal.
            fp = self._prompt_fingerprint(s.prompt)
            if fp != target_fingerprint:
                continue
            # If we get here we have a fingerprint match on an active session.
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
        *,
        block_active_only: bool = True,
        log_fn: Optional[Callable[[str], None]] = None,
    ) -> tuple[Session, bool]:
        """
        Dedup-aware wrapper around :meth:`create_session`.
        Checks for an existing active session with the same prompt fingerprint
        before creating a new one.
        Args:
            (same as :meth:`create_session`)
            block_active_only: See :meth:`check_for_duplicate`.
            log_fn:            Logging callback (default: ``print``).
        Returns:
            ``(session, was_existing)`` — if a duplicate was found, the existing
            session is returned and ``was_existing`` is ``True``.  Otherwise a
            fresh session is created and ``was_existing`` is ``False``.
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
    # ------------------------------------------------------------------
    # High-level: Agent Skills Generation (GitHub Action entry point)
    # ------------------------------------------------------------------
    def run_agent_skills_session(
        self,
        source_name: str,
        starting_branch: str = "main",
        prompt: Optional[str] = None,
        require_plan_approval: bool = False,
        poll_interval: float = DEFAULT_POLL_INTERVAL,
        log_fn: Optional[Callable[[str], None]] = None,
        *,
        # Dedup controls
        skip_if_active: bool = True,
        skip_if_completed: bool = True,
    ) -> Optional[str]:
        """
        End-to-end helper for the Jules GitHub Action.
        Creates (or reuses) a session that analyses the repo, generates Agent
        Skills configuration files, and opens a PR.
        Deduplication behaviour
        -----------------------
        * ``skip_if_active=True``  (default): if an identical session is already
          QUEUED / PLANNING / IN_PROGRESS etc., this call returns the existing
          session's PR URL (or ``None``) without creating a new session.
        * ``skip_if_completed=True`` (default): also skips if a session with the
          same fingerprint COMPLETED successfully within the last scan window.
          Set to ``False`` to allow re-runs after a completed session.
        Args:
            source_name:          Resource name of the source.
            starting_branch:      Branch Jules should work from.
            prompt:               Override the default Agent Skills prompt.
            require_plan_approval: Pause before Jules starts coding.
            poll_interval:        Seconds between activity polls.
            log_fn:               Callable(str) for status messages.
            skip_if_active:       Block duplicate when an active session exists.
            skip_if_completed:    Also block when a completed session exists.
        Returns:
            PR URL string if a pull request was created/found, else ``None``.
        Raises:
            RuntimeError: if the Jules session ends in FAILED state.
        """
        log = log_fn or print
        default_prompt = (
            "Analyze this repository and suggest Agent Skills to improve automation "
            "of common or complex tasks.\\n\\n"
            "Use the Agent Skills specification at https://agentskills.io/specification.md "
            "as the reference for formatting and structuring the skills.\\n\\n"
            "Tasks:\\n"
            "1. Review the repository structure, code, and existing workflows.\\n"
            "2. Identify 1–3 areas where an Agent Skill could be beneficial "
            "(e.g. code review, automated testing, boilerplate generation, "
            "or domain-specific formatting rules).\\n"
            "3. Create the corresponding Agent Skills configuration files "
            "(e.g. in a .jules/skills/ directory, per the specification).\\n"
            "4. Provide a brief explanation of what each skill does and why "
            "it is useful for this repository."
        )
        effective_prompt = prompt or default_prompt
        # ------------------------------------------------------------------
        # Deduplication check BEFORE creating anything
        # ------------------------------------------------------------------
        # When both active AND completed skipping is on, we check against
        # all states; otherwise only active ones.
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
                # Fall through to stream the existing session's remaining activities
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
                # Session exists but is failed/terminal — allow a fresh run
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
            # No duplicate found — create normally
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
        # If the session is already terminal (e.g. we just looked it up),
        # skip the streaming loop.
        if not session.is_terminal:
            for activity in self.stream_activities(
                session.id,
                poll_interval=poll_interval,
                auto_approve_plans=(not require_plan_approval),
            ):
                _log_activity(activity, log)
        final = self.get_session(session.id)
        if final.failed:
            raise RuntimeError(
                f"Jules session '{final.id}' ended in FAILED state."
            )
        prs = final.pull_requests
        if prs:
            pr_url = prs[0].url
            log(f"[Jules] ✓ Pull Request: {pr_url}")
            return pr_url
        log("[Jules] Session finished — no pull request was generated.")
        return None
# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------
def _log_activity(activity: Activity, log: Callable[[str], None]) -> None:
    atype = activity.activity_type
    if atype == "planGenerated":
        plan = Plan.from_dict(activity.payload.get("plan", {}))
        log(f"[Jules] Plan generated — {len(plan.steps)} step(s):")
        for step in plan.steps:
            log(f"         [{step.index + 1}] {step.title}")
    elif atype == "planApproved":
        log(f"[Jules] Plan approved (id={activity.payload.get('planId', '?')})")
    elif atype == "progressUpdated":
        title = activity.payload.get("title", "")
        desc = activity.payload.get("description", "")
        log(f"[Jules] Progress: {title}" + (f" — {desc}" if desc else ""))
    elif atype == "agentMessaged":
        log(f"[Jules] Agent: {activity.payload.get('agentMessage', '')}")
    elif atype == "sessionCompleted":
        log("[Jules] Session completed.")
    elif atype == "sessionFailed":
        raise RuntimeError(
            f"Jules session failed: {activity.payload.get('reason', 'unknown')}"
        )
