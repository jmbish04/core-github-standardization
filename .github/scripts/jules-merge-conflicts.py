#!/usr/bin/env python3
"""
jules-merge-conflicts.py
------------------------
GitHub Action script that uses the modular Jules API client to automatically
resolve git merge conflicts on pull requests.

Environment Variables:
    JULES_API_KEY: Required Jules API key
    GITHUB_REPOSITORY: Repository in owner/repo format
    PR_NUMBER: The Pull Request ID
    HEAD_REF: The branch containing the changes
    BASE_REF: The target branch (usually main)
"""

import os
import sys
from pathlib import Path

# Add the scripts directory to the path so we can import the jules module
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

from jules import JulesClient, AutomationMode
from jules.jules_helpers import get_jules_source_name


def main():
    print("=" * 70)
    print("Jules PR Conflict Resolver")
    print("=" * 70)

    api_key = os.environ.get("JULES_API_KEY")
    repository = os.environ.get("GITHUB_REPOSITORY")
    pr_number = os.environ.get("PR_NUMBER")
    head_ref = os.environ.get("HEAD_REF")
    base_ref = os.environ.get("BASE_REF")

    if not all([api_key, repository, pr_number, head_ref, base_ref]):
        print("ERROR: Missing required environment variables.", file=sys.stderr)
        print("Ensure JULES_API_KEY, GITHUB_REPOSITORY, PR_NUMBER, HEAD_REF, and BASE_REF are set.", file=sys.stderr)
        sys.exit(1)

    owner, repo = repository.split("/")
    source_name = get_jules_source_name(owner, repo)

    print(f"Repository: {repository}")
    print(f"PR Number:  #{pr_number}")
    print(f"Head Ref:   {head_ref}")
    print(f"Base Ref:   {base_ref}")

    # Formulate the instruction prompt for Jules
    prompt = f"""Your task is to resolve git merge conflicts for PR #{pr_number}.

The current feature branch is `{head_ref}` and the base target branch is `{base_ref}`.

Instructions:
1. Fetch and merge the base branch (`{base_ref}`) into the current branch (`{head_ref}`). This will result in merge conflicts.
2. Identify all files with conflict markers (`<<<<<<<`, `=======`, `>>>>>>>`).
3. Carefully analyze both sides of the conflict. Understand the intent of the new changes against the updated base.
4. Resolve the conflicts by editing the files to contain the correct, combined logic. Remove all conflict markers.
5. Ensure the resulting code is syntactically valid and preserves all necessary imports and configurations.
6. Commit the resolved files directly to the `{head_ref}` branch to complete the merge. Do not create a new PR."""

    try:
        client = JulesClient(api_key=api_key)
        print("✓ Jules client initialized")
    except EnvironmentError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    print("\n" + "─" * 70)
    print(f"Creating Jules session for conflict resolution...")
    print("─" * 70)

    try:
        session, was_existing = client.create_session_safe(
            prompt=prompt,
            source_name=source_name,
            starting_branch=head_ref,
            title=f"Resolve Merge Conflicts PR #{pr_number}",
            require_plan_approval=False,
            automation_mode=AutomationMode.AUTO_CREATE_PR,
            block_active_only=True,
            log_fn=print
        )

        if was_existing:
            print(f"[Jules] Reusing existing session: {session.id}")
        else:
            print(f"[Jules] Created new session: {session.id}")

        print(f"[Jules] Session URL: {session.url}")
        print(f"[Jules] Session state: {session.state}")

        if not session.is_terminal:
            print("\n[Jules] Streaming session activities...")
            for activity in client.stream_activities(
                session.id,
                poll_interval=5,
                auto_approve_plans=True
            ):
                if activity.activity_type == "planGenerated":
                    steps = len(activity.payload.get('plan', {}).get('steps', []))
                    print(f"[Jules] Plan generated with {steps} steps.")
                elif activity.activity_type == "progressUpdated":
                    title = activity.payload.get("title", "")
                    print(f"[Jules] Progress: {title}")
                elif activity.activity_type == "sessionCompleted":
                    print("[Jules] Session completed!")
                elif activity.activity_type == "sessionFailed":
                    reason = activity.payload.get("reason", "unknown")
                    print(f"[Jules] ERROR: Session failed: {reason}", file=sys.stderr)

        final_session = client.get_session(session.id)

        print("\n" + "=" * 70)
        if final_session.failed:
            print("ERROR: Jules session failed to resolve the conflicts.", file=sys.stderr)
            print("=" * 70, file=sys.stderr)
            sys.exit(1)

        print("✓ SUCCESS: Conflicts resolved and committed to the branch.")
        print("=" * 70)
        return 0

    except Exception as e:
        print("\n" + "=" * 70, file=sys.stderr)
        print(f"ERROR: Unexpected error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        print("=" * 70, file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
