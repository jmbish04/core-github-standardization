"""
API route handler: test_sessions_api.py

"""

"""Tests for SessionsAPI."""

import pytest
from unittest.mock import Mock, MagicMock

from jules.data_classes import AutomationMode, Session
from jules.sessions import SessionsAPI


"""
TestSessionsAPI — TODO: describe purpose.
"""
class TestSessionsAPI:
    """Tests for SessionsAPI class."""

    @pytest.fixture
    """
    mock_get — TODO: describe purpose.
    
    Args:
        self: TODO: describe self
    
    Returns:
        TODO: describe return value
    """
    def mock_get(self):
        """Create a mock GET function."""
        return Mock()

    @pytest.fixture
    """
    mock_post — TODO: describe purpose.
    
    Args:
        self: TODO: describe self
    
    Returns:
        TODO: describe return value
    """
    def mock_post(self):
        """Create a mock POST function."""
        return Mock()

    @pytest.fixture
    """
    mock_activities_api — TODO: describe purpose.
    
    Args:
        self: TODO: describe self
    
    Returns:
        TODO: describe return value
    """
    def mock_activities_api(self):
        """Create a mock ActivitiesAPI."""
        return Mock()

    @pytest.fixture
    """
    sessions_api — TODO: describe purpose.
    
    Args:
        self: TODO: describe self
        mock_get: TODO: describe mock_get
        mock_post: TODO: describe mock_post
        mock_activities_api: TODO: describe mock_activities_api
    
    Returns:
        TODO: describe return value
    """
    def sessions_api(self, mock_get, mock_post, mock_activities_api):
        """Create a SessionsAPI instance."""
        return SessionsAPI(mock_get, mock_post, mock_activities_api)

    """
    test_create_session — TODO: describe purpose.
    
    Args:
        self: TODO: describe self
        sessions_api: TODO: describe sessions_api
        mock_post: TODO: describe mock_post
        sample_session_dict: TODO: describe sample_session_dict
    
    Returns:
        TODO: describe return value
    """
    def test_create_session(self, sessions_api, mock_post, sample_session_dict):
        """Test creating a session."""
        mock_post.return_value = sample_session_dict

        session = sessions_api.create_session(
            prompt="Test prompt",
            source_name="sources/github--owner--repo",
            starting_branch="main",
        )

        assert session.id == "test123"
        assert session.prompt == "Test prompt"
        mock_post.assert_called_once()

    """
    test_get_session — TODO: describe purpose.
    
    Args:
        self: TODO: describe self
        sessions_api: TODO: describe sessions_api
        mock_get: TODO: describe mock_get
        sample_session_dict: TODO: describe sample_session_dict
    
    Returns:
        TODO: describe return value
    """
    def test_get_session(self, sessions_api, mock_get, sample_session_dict):
        """Test getting a session."""
        mock_get.return_value = sample_session_dict

        session = sessions_api.get_session("test123")

        assert session.id == "test123"
        mock_get.assert_called_once_with("sessions/test123", None)

    """
    test_get_session_with_full_name — TODO: describe purpose.
    
    Args:
        self: TODO: describe self
        sessions_api: TODO: describe sessions_api
        mock_get: TODO: describe mock_get
        sample_session_dict: TODO: describe sample_session_dict
    
    Returns:
        TODO: describe return value
    """
    def test_get_session_with_full_name(self, sessions_api, mock_get, sample_session_dict):
        """Test getting a session with full resource name."""
        mock_get.return_value = sample_session_dict

        session = sessions_api.get_session("sessions/test123")

        assert session.id == "test123"
        mock_get.assert_called_once_with("sessions/test123", None)

    """
    test_list_sessions — TODO: describe purpose.
    
    Args:
        self: TODO: describe self
        sessions_api: TODO: describe sessions_api
        mock_get: TODO: describe mock_get
        sample_session_dict: TODO: describe sample_session_dict
    
    Returns:
        TODO: describe return value
    """
    def test_list_sessions(self, sessions_api, mock_get, sample_session_dict):
        """Test listing sessions."""
        mock_get.return_value = {
            "sessions": [sample_session_dict],
            "nextPageToken": "token123",
        }

        result = sessions_api.list_sessions(page_size=30)

        assert len(result["sessions"]) == 1
        assert result["nextPageToken"] == "token123"
        mock_get.assert_called_once()

    """
    test_approve_plan — TODO: describe purpose.
    
    Args:
        self: TODO: describe self
        sessions_api: TODO: describe sessions_api
        mock_post: TODO: describe mock_post
    
    Returns:
        TODO: describe return value
    """
    def test_approve_plan(self, sessions_api, mock_post):
        """Test approving a plan."""
        mock_post.return_value = {}

        sessions_api.approve_plan("test123")

        mock_post.assert_called_once_with("sessions/test123:approvePlan", None)

    """
    test_send_message — TODO: describe purpose.
    
    Args:
        self: TODO: describe self
        sessions_api: TODO: describe sessions_api
        mock_post: TODO: describe mock_post
    
    Returns:
        TODO: describe return value
    """
    def test_send_message(self, sessions_api, mock_post):
        """Test sending a message."""
        mock_post.return_value = {}

        sessions_api.send_message("test123", "Hello")

        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == "sessions/test123:sendMessage"
        assert call_args[0][1] == {"prompt": "Hello"}
