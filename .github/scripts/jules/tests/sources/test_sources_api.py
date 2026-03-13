"""Tests for SourcesAPI."""

import pytest
from unittest.mock import Mock

from jules.sources import SourcesAPI


class TestSourcesAPI:
    """Tests for SourcesAPI class."""

    @pytest.fixture
    def mock_get(self):
        """Create a mock GET function."""
        return Mock()

    @pytest.fixture
    def sources_api(self, mock_get):
        """Create a SourcesAPI instance."""
        return SourcesAPI(mock_get)

    def test_list_sources(self, sources_api, mock_get):
        """Test listing sources."""
        mock_get.return_value = {
            "sources": [
                {"name": "sources/github--owner1--repo1"},
                {"name": "sources/github--owner2--repo2"},
            ]
        }

        sources = sources_api.list_sources()

        assert len(sources) == 2
        mock_get.assert_called_once_with("sources", None)

    def test_get_source(self, sources_api, mock_get):
        """Test getting a single source."""
        mock_get.return_value = {"name": "sources/github--owner--repo"}

        source = sources_api.get_source("sources/github--owner--repo")

        assert source["name"] == "sources/github--owner--repo"
        mock_get.assert_called_once_with("sources/github--owner--repo", None)

    def test_find_source_for_repo_found(self, sources_api, mock_get):
        """Test finding a source by owner/repo."""
        mock_get.return_value = {
            "sources": [
                {
                    "name": "sources/github--owner1--repo1",
                    "githubRepo": {"owner": "owner1", "repo": "repo1"},
                },
                {
                    "name": "sources/github--owner2--repo2",
                    "githubRepo": {"owner": "owner2", "repo": "repo2"},
                },
            ]
        }

        source = sources_api.find_source_for_repo("owner2", "repo2")

        assert source is not None
        assert source["name"] == "sources/github--owner2--repo2"

    def test_find_source_for_repo_not_found(self, sources_api, mock_get):
        """Test finding a source that doesn't exist."""
        mock_get.return_value = {
            "sources": [
                {
                    "name": "sources/github--owner1--repo1",
                    "githubRepo": {"owner": "owner1", "repo": "repo1"},
                },
            ]
        }

        source = sources_api.find_source_for_repo("owner2", "repo2")

        assert source is None

    def test_find_source_case_insensitive(self, sources_api, mock_get):
        """Test that find_source_for_repo is case-insensitive."""
        mock_get.return_value = {
            "sources": [
                {
                    "name": "sources/github--Owner--Repo",
                    "githubRepo": {"owner": "Owner", "repo": "Repo"},
                },
            ]
        }

        source = sources_api.find_source_for_repo("owner", "repo")

        assert source is not None
        assert source["name"] == "sources/github--Owner--Repo"
