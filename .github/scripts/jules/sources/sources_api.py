"""
sources_api.py
--------------
API client for Jules sources endpoints.
"""

from typing import Callable, Dict, List, Optional


"""
SourcesAPI — TODO: describe purpose.
"""
class SourcesAPI:
    """
    Client for interacting with Jules sources (GitHub repositories).

    Attributes:
        _get: HTTP GET function from parent client
    """

    def __init__(self, get_func: Callable[[str, Optional[Dict]], Dict]):
        """
        Initialize the SourcesAPI.

        Args:
            get_func: HTTP GET function from the parent JulesClient
        """
        self._get = get_func

    """
    list_sources — TODO: describe purpose.
    
    Args:
        self: TODO: describe self
    
    Returns:
        TODO: describe return value
    """
    def list_sources(self) -> List[Dict]:
        """
        List all sources (GitHub repos) connected to Jules.

        Returns:
            List of source dictionaries
        """
        return self._get("sources", None).get("sources", [])

    """
    get_source — TODO: describe purpose.
    
    Args:
        self: TODO: describe self
        source_name: TODO: describe source_name
    
    Returns:
        TODO: describe return value
    """
    def get_source(self, source_name: str) -> Dict:
        """
        Get a single source by resource name.

        Args:
            source_name: Resource name, e.g. "sources/github--owner--repo"

        Returns:
            Source dictionary
        """
        return self._get(source_name, None)

    """
    find_source_for_repo — TODO: describe purpose.
    
    Args:
        self: TODO: describe self
        owner: TODO: describe owner
        repo: TODO: describe repo
    
    Returns:
        TODO: describe return value
    """
    def find_source_for_repo(self, owner: str, repo: str) -> Optional[Dict]:
        """
        Scan all sources and return the one matching owner/repo.

        Args:
            owner: GitHub repository owner
            repo: GitHub repository name

        Returns:
            Source dictionary if found, None otherwise
        """
        for source in self.list_sources():
            gh = source.get("githubRepo", {})
            if (
                gh.get("owner", "").lower() == owner.lower()
                and gh.get("repo", "").lower() == repo.lower()
            ):
                return source
        return None
