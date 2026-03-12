#!/usr/bin/env python3
"""
jules-generate-agent-instructions.py
-------------------------------------
GitHub Action script that uses Jules API to generate/update agent instructions
across multiple configuration locations.

This script:
1. Connects to Jules API using the modular client
2. Creates a session to generate agent instructions
3. Updates the following files/directories:
   - .agent/rules/ (agent-specific rules)
   - .agent/workflows/ (workflow definitions)
   - AGENTS.md (agent documentation)
   - CLAUDE.md (Claude-specific instructions)
   - .copilot/agents/custom.agent.md (Copilot agent config)

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


def main():
    """
    Main entry point for the agent instructions generation workflow.

    Workflow:
        1. Extract repository context from environment
        2. Connect to Jules API
        3. Create or reuse a session for generating agent instructions
        4. Stream activities and wait for completion
        5. Return PR URL if created
    """
    print("=" * 70)
    print("Jules Agent Instructions Generator")
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

    # Custom prompt for agent instructions generation
    prompt = """Analyze this repository and generate comprehensive agent instructions
to help AI agents understand how to work effectively with this codebase.

Review the existing:
- Code structure and patterns
- Development workflows
- Testing practices
- Documentation conventions
- Common tasks and operations

Then create or update agent instructions in the following locations:

1. .agent/rules/ - Create rule files that define:
   - Code style and conventions
   - Testing requirements
   - Documentation standards
   - Security best practices
   - Common pitfalls to avoid

2. .agent/workflows/ - Create workflow files that describe:
   - Development workflow (branch, commit, PR process)
   - Build and deployment process
   - Testing and validation steps
   - Release procedures

3. AGENTS.md - Update this file with:
   - Overview of available agents
   - When to use each agent
   - Agent capabilities and limitations
   - Examples of agent usage

4. CLAUDE.md - Update Claude-specific instructions including:
   - Project-specific context
   - Preferred approaches for common tasks
   - Important architectural decisions
   - Domain-specific knowledge

5. .copilot/agents/custom.agent.md - Update Copilot agent configuration:
   - Custom agent behaviors
   - Context-specific guidance
   - Integration with repository workflows

IMPORTANT:
- Make instructions clear, concise, and actionable
- Include examples where helpful
- Keep instructions up-to-date with current codebase
- Focus on what makes this repository unique"""

    print("\n" + "─" * 70)
    print("Creating Jules session for agent instructions generation...")
    print("─" * 70)

    # Run the session with custom title and deduplication
    try:
        # Use the low-level API for more control
        session, was_existing = client.create_session_safe(
            prompt=prompt,
            source_name=source_name,
            starting_branch=context["branch"],
            title="Generate Agent Instructions",
            require_plan_approval=False,
            block_active_only=True,
            log_fn=print,
        )

        if was_existing:
            print(f"[Jules] Reusing existing session: {session.id}")
        else:
            print(f"[Jules] Created new session: {session.id}")

        print(f"[Jules] Session URL: {session.url}")
        print(f"[Jules] Session state: {session.state}")

        # Stream activities if session is not already terminal
        if not session.is_terminal:
            print("\n[Jules] Streaming session activities...")
            for activity in client.stream_activities(
                session.id,
                poll_interval=5,
                auto_approve_plans=True,
            ):
                # Log activity details
                if activity.activity_type == "planGenerated":
                    print(f"[Jules] Plan generated with {len(activity.payload.get('plan', {}).get('steps', []))} steps")
                elif activity.activity_type == "progressUpdated":
                    title = activity.payload.get("title", "")
                    print(f"[Jules] Progress: {title}")
                elif activity.activity_type == "sessionCompleted":
                    print("[Jules] Session completed!")
                elif activity.activity_type == "sessionFailed":
                    reason = activity.payload.get("reason", "unknown")
                    print(f"[Jules] ERROR: Session failed: {reason}", file=sys.stderr)

        # Get final session state
        final_session = client.get_session(session.id)

        print("\n" + "=" * 70)
        if final_session.failed:
            print(f"ERROR: Jules session failed", file=sys.stderr)
            print("=" * 70, file=sys.stderr)
            return 1

        # Check for pull requests
        prs = final_session.pull_requests
        if prs:
            pr_url = prs[0].url
            print(f"✓ SUCCESS: Pull request created")
            print(f"  URL: {pr_url}")
            print("\nAgent instructions have been generated/updated in:")
            print("  - .agent/rules/")
            print("  - .agent/workflows/")
            print("  - AGENTS.md")
            print("  - CLAUDE.md")
            print("  - .copilot/agents/custom.agent.md")
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
