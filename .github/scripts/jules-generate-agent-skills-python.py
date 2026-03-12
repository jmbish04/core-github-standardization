"""
Script: jules-generate-agent-skills-python.py

"""

#!/usr/bin/env python3
"""
jules-generate-agent-skills.py
-------------------------------
GitHub Action script that uses Jules API to generate agent skills
and places them in multiple standard locations.

This script:
1. Connects to Jules API using the modular client
2. Creates a session to generate agent skills
3. Waits for the session to complete
4. Extracts generated skills and places them in:
   - .copilot/skills/
   - .github/skills/
   - .agent/skills/

Environment Variables:
    JULES_API_KEY: Required Jules API key
    GITHUB_REPOSITORY: Repository in owner/repo format
    GITHUB_REF: Git reference (branch/tag)
"""

import os
import sys
from pathlib import Path

# Add the scripts directory to the path so we can import jules module
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

from jules import JulesClient
from jules.jules_helpers import get_repo_context, get_jules_source_name


"""
main — TODO: describe purpose.

Returns:
    TODO: describe return value
"""
def main():
    """
    Main entry point for the agent skills generation workflow.

    Workflow:
        1. Extract repository context from environment
        2. Connect to Jules API
        3. Create or reuse a session for generating agent skills
        4. Stream activities and wait for completion
        5. Return PR URL if created
    """
    print("=" * 70)
    print("Jules Agent Skills Generator")
    print("=" * 70)

    # Get repository context from environment
    try:
        context = get_repo_context()
        print(f"Repository: {context['repository']}")
        print(f"Branch: {context['branch']}")
    except (EnvironmentError, ValueError) as e:
        print(f"ERROR: Failed to get repository context: {e}", file=sys.stderr)
        sys.exit(1)

    # Initialize Jules client
    try:
        client = JulesClient()
        print("✓ Jules client initialized")
    except EnvironmentError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    # Build the Jules source name
    source_name = get_jules_source_name(context["owner"], context["repo"])
    print(f"Source: {source_name}")

    # Custom prompt for agent skills generation with multiple output locations
    prompt = """Analyze this repository and generate Agent Skills to improve automation
of common or complex tasks.

Use the Agent Skills specification at https://agentskills.io/specification.md
as the reference for formatting and structuring the skills.

Tasks:
1. Review the repository structure, code, and existing workflows.
2. Identify 1-3 areas where an Agent Skill could be beneficial
   (e.g. code review, automated testing, boilerplate generation,
   or domain-specific formatting rules).
3. Create the corresponding Agent Skills configuration files in
   ALL of the following directories:
   - .copilot/skills/
   - .github/skills/
   - .agent/skills/
4. Provide a brief explanation of what each skill does and why
   it is useful for this repository.

IMPORTANT: Create the skill files in ALL THREE directories listed above.
Each directory should contain the same set of skills."""

    print("\n" + "─" * 70)
    print("Creating Jules session for agent skills generation...")
    print("─" * 70)

    # Run the agent skills session with deduplication
    try:
        pr_url = client.run_agent_skills_session(
            source_name=source_name,
            starting_branch=context["branch"],
            prompt=prompt,
            require_plan_approval=False,
            log_fn=print,
            skip_if_active=True,
            skip_if_completed=True,
        )

        print("\n" + "=" * 70)
        if pr_url:
            print(f"✓ SUCCESS: Pull request created")
            print(f"  URL: {pr_url}")
            print("\nThe agent skills have been generated in:")
            print("  - .copilot/skills/")
            print("  - .github/skills/")
            print("  - .agent/skills/")
        else:
            print("✓ Session completed without creating a pull request")
            print("  (This may happen if no changes were needed)")

        print("=" * 70)
        return 0

    except RuntimeError as e:
        print("\n" + "=" * 70, file=sys.stderr)
        print(f"ERROR: Jules session failed: {e}", file=sys.stderr)
        print("=" * 70, file=sys.stderr)
        return 1

    except Exception as e:
        print("\n" + "=" * 70, file=sys.stderr)
        print(f"ERROR: Unexpected error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        print("=" * 70, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
