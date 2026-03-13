"""
jules_client.py
---------------
Main client for the Jules REST API (v1alpha).

Designed to be used inside a Jules GitHub Action to generate Agent Skills
and manage coding sessions.

Environment:
    JULES_API_KEY – required Google API key with Jules API access
"""

import logging
import os
from typing import Optional

import requests

from .config import BASE_URL, DEFAULT_TIMEOUT
from .sessions.activities_api import ActivitiesAPI
from .sessions.sessions_api import SessionsAPI
from .sources.sources_api import SourcesAPI

logger = logging.getLogger(__name__)


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

    Attributes:
        api_key: Google API key for Jules authentication
        timeout: HTTP request timeout in seconds
        sources: SourcesAPI instance for source operations
        sessions: SessionsAPI instance for session operations
        activities: ActivitiesAPI instance for activity operations
    """

    def __init__(self, api_key: Optional[str] = None, timeout: int = DEFAULT_TIMEOUT):
        """
        Initialize the JulesClient.

        Args:
            api_key: Google API key (defaults to JULES_API_KEY env var)
            timeout: HTTP request timeout in seconds

        Raises:
            EnvironmentError: If JULES_API_KEY is not set and api_key not provided
        """
        self.api_key = api_key or os.environ.get("JULES_API_KEY")
        if not self.api_key:
            raise EnvironmentError(
                "Jules API key not found. "
                "Set JULES_API_KEY env var or pass api_key= to JulesClient()."
            )
        self.timeout = timeout
        self._session = requests.Session()
        self._session.headers.update({"Content-Type": "application/json"})

        # Initialize API components
        self.activities = ActivitiesAPI(self._get, self._post)
        self.sessions = SessionsAPI(self._get, self._post, self.activities)
        self.sources = SourcesAPI(self._get)

        # Set up circular dependency for activities API
        self.activities.set_get_session_func(self.sessions.get_session)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _url(self, path: str) -> str:
        """
        Construct full URL from path.

        Args:
            path: API path (with or without leading slash)

        Returns:
            Full URL
        """
        return f"{BASE_URL}/{path.lstrip('/')}"

    def _params(self, extra: Optional[dict] = None) -> dict:
        """
        Build query parameters with API key.

        Args:
            extra: Additional query parameters

        Returns:
            Dictionary of query parameters
        """
        p = {"key": self.api_key}
        if extra:
            p.update(extra)
        return p

    def _get(self, path: str, params: Optional[dict] = None) -> dict:
        """
        Make a GET request to the Jules API.

        Args:
            path: API path
            params: Additional query parameters

        Returns:
            Parsed JSON response

        Raises:
            requests.HTTPError: On HTTP error status
        """
        resp = self._session.get(
            self._url(path), params=self._params(params), timeout=self.timeout
        )
        resp.raise_for_status()
        return resp.json()

    def _post(self, path: str, body: Optional[dict] = None) -> dict:
        """
        Make a POST request to the Jules API.

        Args:
            path: API path
            body: Request body (JSON)

        Returns:
            Parsed JSON response

        Raises:
            requests.HTTPError: On HTTP error status
        """
        resp = self._session.post(
            self._url(path), params=self._params(), json=body or {}, timeout=self.timeout
        )
        resp.raise_for_status()
        try:
            return resp.json() if resp.content else {}
        except ValueError:
            return {}

    # ------------------------------------------------------------------
    # Convenience methods (delegate to sub-APIs)
    # ------------------------------------------------------------------

    def list_sources(self):
        """List all sources (GitHub repos) connected to Jules."""
        return self.sources.list_sources()

    def get_source(self, source_name: str):
        """Get a single source by resource name."""
        return self.sources.get_source(source_name)

    def find_source_for_repo(self, owner: str, repo: str):
        """Scan all sources and return the one matching owner/repo."""
        return self.sources.find_source_for_repo(owner, repo)

    def create_session(self, *args, **kwargs):
        """Create a new Jules session (raw, no dedup check)."""
        return self.sessions.create_session(*args, **kwargs)

    def get_session(self, session_id: str):
        """Get a session by bare ID or full resource name."""
        return self.sessions.get_session(session_id)

    def list_sessions(self, *args, **kwargs):
        """List sessions with pagination."""
        return self.sessions.list_sessions(*args, **kwargs)

    def list_all_sessions(self, *args, **kwargs):
        """Fetch up to max_pages pages of sessions."""
        return self.sessions.list_all_sessions(*args, **kwargs)

    def approve_plan(self, session_id: str):
        """Approve the pending plan in a session."""
        return self.sessions.approve_plan(session_id)

    def send_message(self, session_id: str, prompt: str):
        """Send a follow-up message to an active session."""
        return self.sessions.send_message(session_id, prompt)

    def check_for_duplicate(self, *args, **kwargs):
        """Scan existing sessions to determine if an equivalent exists."""
        return self.sessions.check_for_duplicate(*args, **kwargs)

    def create_session_safe(self, *args, **kwargs):
        """Dedup-aware wrapper around create_session."""
        return self.sessions.create_session_safe(*args, **kwargs)

    def run_agent_skills_session(self, *args, **kwargs):
        """End-to-end helper for the Jules GitHub Action."""
        return self.sessions.run_agent_skills_session(*args, **kwargs)

    def get_activity(self, session_id: str, activity_id: str):
        """Get a specific activity from a session."""
        return self.activities.get_activity(session_id, activity_id)

    def list_activities(self, *args, **kwargs):
        """List activities for a session with pagination."""
        return self.activities.list_activities(*args, **kwargs)

    def stream_activities(self, *args, **kwargs):
        """Poll activities list, yielding each new Activity."""
        return self.activities.stream_activities(*args, **kwargs)
