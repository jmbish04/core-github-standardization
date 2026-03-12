"""
Script: jules-cloudflare-fix.py

"""

#!/usr/bin/env python3
"""
jules-cloudflare-fix.py
-----------------------
GitHub Action script that analyzes failed Cloudflare deployments and uses
Jules API to automatically fix build errors.

This script:
1. Fetches Cloudflare project and deployment information
2. Retrieves build logs from failed deployments
3. Uses Jules API to analyze errors and push fixes

Environment Variables:
    CLOUDFLARE_API_TOKEN: Cloudflare API token
    CLOUDFLARE_ACCOUNT_ID: Cloudflare account ID
    JULES_API_KEY: Jules API key
    GITHUB_REPOSITORY: Repository in owner/repo format
    GITHUB_HEAD_REF: Branch name (for PRs)
    GITHUB_REF_NAME: Fallback branch name
"""

import os
import sys
from pathlib import Path

import requests

# Add the scripts directory to the path so we can import jules module
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

from jules import JulesClient, AutomationMode
from jules.jules_helpers import get_repo_context, get_jules_source_name


"""
main — TODO: describe purpose.

Returns:
    TODO: describe return value
"""
def main():
    """
    Main entry point for Cloudflare build error remediation.

    Workflow:
        1. Validate environment variables
        2. Find Cloudflare project linked to GitHub repo
        3. Get latest deployment for the current branch
        4. Check if deployment failed
        5. Retrieve deployment logs
        6. Use Jules to analyze and fix the error
    """
    print("=" * 70)
    print("Jules Cloudflare Build Fix")
    print("=" * 70)

    # Validate environment variables
    api_token = os.environ.get("CLOUDFLARE_API_TOKEN")
    account_id = os.environ.get("CLOUDFLARE_ACCOUNT_ID")
    jules_api_key = os.environ.get("JULES_API_KEY")
    github_repository = os.environ.get("GITHUB_REPOSITORY", "")

    # Get branch name - prefer GITHUB_HEAD_REF (PR) over GITHUB_REF_NAME
    github_ref = os.environ.get("GITHUB_HEAD_REF") or os.environ.get("GITHUB_REF_NAME", "")

    if not all([api_token, account_id, jules_api_key, github_repository]):
        print(
            "ERROR: Missing required environment variables:",
            file=sys.stderr
        )
        print("  CLOUDFLARE_API_TOKEN, CLOUDFLARE_ACCOUNT_ID,", file=sys.stderr)
        print("  JULES_API_KEY, GITHUB_REPOSITORY", file=sys.stderr)
        sys.exit(1)

    repo_name = github_repository.split("/")[-1]
    owner, repo = github_repository.split("/")

    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }

    print(f"Repository: {github_repository}")
    print(f"Branch: {github_ref}")
    print(f"Searching for Cloudflare project: {repo_name}")

    # 1. Fetch Cloudflare projects to find the matching repository
    projects_url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/pages/projects"
    resp = requests.get(projects_url, headers=headers)

    if resp.status_code != 200:
        print(f"ERROR: Failed to fetch Cloudflare projects: {resp.text}", file=sys.stderr)
        sys.exit(1)

    projects = resp.json().get("result", [])
    target_project = None

    for proj in projects:
        source = proj.get("source", {})
        if source.get("type") == "github" and source.get("config", {}).get("repo_name") == repo_name:
            target_project = proj["name"]
            break

    if not target_project:
        print(f"WARNING: Could not find Cloudflare project linked to '{repo_name}'")
        print("Exiting gracefully - no action needed")
        sys.exit(0)

    print(f"✓ Found Cloudflare project: {target_project}")

    # 2. Get deployments for the specific project
    print(f"Fetching latest deployment for branch: {github_ref}")
    deployments_url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/pages/projects/{target_project}/deployments"
    dep_resp = requests.get(deployments_url, headers=headers)

    if dep_resp.status_code != 200:
        print(f"ERROR: Failed to fetch deployments: {dep_resp.text}", file=sys.stderr)
        sys.exit(1)

    deployments = dep_resp.json().get("result", [])
    target_deployment = None
    build_status = None

    for dep in deployments:
        # Match the deployment to the active PR branch
        if dep.get("deployment_trigger", {}).get("metadata", {}).get("branch") == github_ref:
            target_deployment = dep["id"]
            build_status = dep.get("latest_stage", {}).get("status")
            break

    if not target_deployment:
        print("WARNING: Could not find deployment for this branch")
        print("Skipping Jules analysis")
        sys.exit(0)

    print(f"✓ Found deployment: {target_deployment}")
    print(f"  Build status: {build_status}")

    # Only invoke Jules if the Cloudflare build actually failed
    if build_status in ["success", "active"]:
        print(f"Build status is '{build_status}' - no remediation required")
        sys.exit(0)

    print("Build failed - fetching logs...")

    # 3. Get the deployment logs
    logs_url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/pages/projects/{target_project}/deployments/{target_deployment}/history/logs"
    logs_resp = requests.get(logs_url, headers=headers)

    if logs_resp.status_code != 200:
        print(f"ERROR: Failed to fetch deployment logs: {logs_resp.text}", file=sys.stderr)
        sys.exit(1)

    logs_data = logs_resp.json().get("result", {}).get("data", [])

    # Combine logs into a single string. Keep the tail end if it exceeds reasonable context limits.
    full_logs = "\n".join([line.get("line", "") for line in logs_data])
    if len(full_logs) > 15000:
        full_logs = "... [TRUNCATED] ...\n" + full_logs[-15000:]

    if not full_logs.strip():
        print("WARNING: No logs found for the failed build")
        sys.exit(0)

    print(f"✓ Retrieved {len(logs_data)} log lines")
    print("\n" + "─" * 70)
    print("Invoking Jules to analyze and fix the build error...")
    print("─" * 70)

    # 4. Build the prompt with the logs
    prompt = f"""The Cloudflare CI/CD build recently failed for this repository.
Analyze the following build logs and implement the necessary codebase fix to resolve the error.

Pay close attention to these common failure modes:
1. **Entrypoint Mismatch:** The `main` or `entrypoint` defined in `wrangler.jsonc`
   (or `wrangler.toml`) does not match the actual application entry file
   (e.g., pointing to src/index.ts instead of src/main.ts).
2. **Missing Assets:** The `ASSETS` binding is pointing to a static output directory
   (like `dist`, `build`, or `public`) that does not exist or was not generated
   by the build step.
3. **Frozen Lockfiles:** The CI environment uses a frozen lockfile by default.
   If `pnpm-lock.yaml`, `bun.lockb`, or `package-lock.json` is out of sync with
   `package.json`, the dependency installation will fail. You must sync the
   dependencies or adjust the package configurations.

Build Logs:
```
{full_logs}
```

Identify the root cause from the logs, make the necessary file modifications,
and apply the fix directly to the current branch: {github_ref}"""

    # 5. Initialize Jules client and create session
    try:
        client = JulesClient()
        print("✓ Jules client initialized")
    except EnvironmentError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    source_name = get_jules_source_name(owner, repo)
    print(f"Source: {source_name}")

    try:
        # Create session with auto PR disabled (commit to current branch)
        session = client.create_session(
            prompt=prompt,
            source_name=source_name,
            starting_branch=github_ref,
            title="Fix Cloudflare Build Error",
            require_plan_approval=False,
            automation_mode=AutomationMode.AUTO_CREATE_PR,
        )

        print(f"✓ Session created: {session.id}")
        print(f"  URL: {session.url}")
        print(f"  State: {session.state}")

        # Stream activities
        print("\n[Jules] Streaming session activities...")
        for activity in client.stream_activities(
            session.id,
            poll_interval=5,
            auto_approve_plans=True,
        ):
            if activity.activity_type == "planGenerated":
                plan = activity.payload.get("plan", {})
                steps = plan.get("steps", [])
                print(f"[Jules] Plan generated with {len(steps)} steps")
            elif activity.activity_type == "progressUpdated":
                title = activity.payload.get("title", "")
                print(f"[Jules] Progress: {title}")
            elif activity.activity_type == "sessionCompleted":
                print("[Jules] Session completed!")
            elif activity.activity_type == "sessionFailed":
                reason = activity.payload.get("reason", "unknown")
                raise RuntimeError(f"Session failed: {reason}")

        # Get final session state
        final_session = client.get_session(session.id)

        print("\n" + "=" * 70)
        if final_session.failed:
            print("ERROR: Jules session failed to resolve the issue", file=sys.stderr)
            print("=" * 70, file=sys.stderr)
            sys.exit(1)

        prs = final_session.pull_requests
        if prs:
            pr_url = prs[0].url
            print(f"✓ SUCCESS: Pull request created with fix")
            print(f"  URL: {pr_url}")
        else:
            print("✓ Session completed - check the branch for committed fixes")

        print("=" * 70)
        return 0

    except RuntimeError as e:
        print("\n" + "=" * 70, file=sys.stderr)
        print(f"ERROR: {e}", file=sys.stderr)
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
