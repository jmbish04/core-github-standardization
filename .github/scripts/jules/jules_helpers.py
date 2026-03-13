"""
jules_helpers.py
----------------
Helper utilities for Jules GitHub Actions workflows.

This module provides convenience functions for:
- Creating skills in multiple standard locations
- Generating agent instructions
- Common GitHub/Jules integration patterns

Functions:
    create_skill_files: Create agent skills in multiple locations
    create_instruction_files: Create agent instruction files
    get_repo_context: Extract repository context from environment
"""

import os
from pathlib import Path
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Constants for standard agent directories
# ---------------------------------------------------------------------------
SKILL_DIRECTORIES = [
    ".copilot/skills",
    ".github/skills",
    ".agent/skills",
]

INSTRUCTION_FILES = {
    "rules": ".agent/rules",
    "workflows": ".agent/workflows",
    "agents_md": "AGENTS.md",
    "claude_md": "CLAUDE.md",
    "copilot_agent": ".copilot/agents/custom.agent.md",
}


# ---------------------------------------------------------------------------
# Repository context helpers
# ---------------------------------------------------------------------------
def get_repo_context() -> Dict[str, str]:
    """
    Extract repository context from GitHub Actions environment.

    Returns:
        Dict with keys: repository, owner, repo, ref, branch, sha

    Raises:
        EnvironmentError: If required environment variables are missing
    """
    repository = os.environ.get("GITHUB_REPOSITORY", "")
    if not repository:
        raise EnvironmentError("GITHUB_REPOSITORY environment variable is required")

    parts = repository.split("/")
    if len(parts) != 2:
        raise ValueError(f"Invalid GITHUB_REPOSITORY format: {repository}")

    owner, repo = parts
    ref = os.environ.get("GITHUB_REF", "refs/heads/main")
    sha = os.environ.get("GITHUB_SHA", "")

    # Extract branch name from ref
    branch = ref
    if ref.startswith("refs/heads/"):
        branch = ref.replace("refs/heads/", "")
    elif ref.startswith("refs/tags/"):
        branch = ref.replace("refs/tags/", "")

    return {
        "repository": repository,
        "owner": owner,
        "repo": repo,
        "ref": ref,
        "branch": branch,
        "sha": sha,
    }


# ---------------------------------------------------------------------------
# Skill file creation helpers
# ---------------------------------------------------------------------------
def create_skill_files(
    skill_name: str,
    skill_content: str,
    base_path: Optional[str] = None,
    directories: Optional[List[str]] = None,
) -> List[str]:
    """
    Create a skill file in multiple standard locations.

    Args:
        skill_name: Name of the skill file (e.g., "code-review.md")
        skill_content: Content of the skill file
        base_path: Base path for relative directories (defaults to cwd)
        directories: List of directories to create skills in (defaults to SKILL_DIRECTORIES)

    Returns:
        List of created file paths

    Example:
        created = create_skill_files(
            "code-review.md",
            "# Code Review Skill\\n\\nReview code for best practices."
        )
    """
    if base_path is None:
        base_path = os.getcwd()

    if directories is None:
        directories = SKILL_DIRECTORIES

    created_files = []

    for directory in directories:
        dir_path = Path(base_path) / directory
        dir_path.mkdir(parents=True, exist_ok=True)

        file_path = dir_path / skill_name
        file_path.write_text(skill_content, encoding="utf-8")
        created_files.append(str(file_path))

    return created_files


# ---------------------------------------------------------------------------
# Instruction file creation helpers
# ---------------------------------------------------------------------------
def create_instruction_files(
    instructions: Dict[str, str],
    base_path: Optional[str] = None,
) -> List[str]:
    """
    Create agent instruction files in standard locations.

    Args:
        instructions: Dict mapping instruction type to content
            Valid keys: "rules", "workflows", "agents_md", "claude_md", "copilot_agent"
        base_path: Base path for relative paths (defaults to cwd)

    Returns:
        List of created/updated file paths

    Example:
        created = create_instruction_files({
            "rules": "# Agent Rules\\n\\n1. Always test code",
            "agents_md": "# Agents\\n\\nCustom agents for this repo",
        })
    """
    if base_path is None:
        base_path = os.getcwd()

    created_files = []

    for inst_type, content in instructions.items():
        if inst_type not in INSTRUCTION_FILES:
            raise ValueError(
                f"Invalid instruction type: {inst_type}. "
                f"Valid types: {list(INSTRUCTION_FILES.keys())}"
            )

        file_path = Path(base_path) / INSTRUCTION_FILES[inst_type]

        # For directory-based instructions, create as a file in that directory
        if inst_type in ["rules", "workflows"]:
            file_path.mkdir(parents=True, exist_ok=True)
            # In this case, content should be dict of filename -> content
            if isinstance(content, dict):
                for filename, file_content in content.items():
                    instruction_file = file_path / filename
                    instruction_file.write_text(file_content, encoding="utf-8")
                    created_files.append(str(instruction_file))
            else:
                # Single file with default name
                instruction_file = file_path / "default.md"
                instruction_file.write_text(content, encoding="utf-8")
                created_files.append(str(instruction_file))
        else:
            # Single file instructions
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")
            created_files.append(str(file_path))

    return created_files


# ---------------------------------------------------------------------------
# Jules source name helpers
# ---------------------------------------------------------------------------
def get_jules_source_name(owner: str, repo: str) -> str:
    """
    Format a Jules source name from owner and repo.

    Args:
        owner: GitHub repository owner
        repo: GitHub repository name

    Returns:
        Jules source name (e.g., "sources/github--owner--repo")
    """
    return f"sources/github--{owner}--{repo}"


def parse_jules_source_name(source_name: str) -> tuple[str, str]:
    """
    Parse a Jules source name into owner and repo.

    Args:
        source_name: Jules source name (e.g., "sources/github--owner--repo")

    Returns:
        Tuple of (owner, repo)

    Raises:
        ValueError: If source name format is invalid
    """
    if not source_name.startswith("sources/github--"):
        raise ValueError(f"Invalid source name format: {source_name}")

    parts = source_name.replace("sources/github--", "").split("--")
    if len(parts) != 2:
        raise ValueError(f"Invalid source name format: {source_name}")

    return parts[0], parts[1]
