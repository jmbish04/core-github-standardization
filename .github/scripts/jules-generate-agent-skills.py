import os
import sys
import asyncio

try:
    # Assuming the Python SDK exposes the client similarly
    from google_jules import jules
except ImportError as e:
    print(f"::error::Failed to dynamically import google_jules: {e}")
    sys.exit(1)

async def run():
    if not os.environ.get("JULES_API_KEY"):
        print("::error::JULES_API_KEY environment variable is missing.")
        sys.exit(1)

    # 1. Get context about the current repository from environment variables
    github_repository = os.environ.get("GITHUB_REPOSITORY", "")
    repo_parts = github_repository.split("/")
    owner = repo_parts[0] if len(repo_parts) > 0 and repo_parts[0] else "unknown"
    repo = repo_parts[1] if len(repo_parts) > 1 and repo_parts[1] else "unknown"
    ref = os.environ.get("GITHUB_REF", "refs/heads/main")

    base_branch = "main"
    if ref.startswith("refs/heads/"):
        base_branch = ref.replace("refs/heads/", "")

    print(f"Starting Jules session for {owner}/{repo} on branch {base_branch}")

    # 2. Construct the prompt for generating Agent Skills
    prompt = """Analyze this repository and suggest Agent Skills to improve automation of common or complex tasks.

Use the Agent Skills specification located at https://agentskills.io/specification.md as a reference for formatting and structuring the skills.

Tasks:
1. Review the repository structure, code, and existing workflows.
2. Identify 1 to 3 areas where an Agent Skill could be beneficial (e.g., code review, automated testing, boilerplate generation, or specific formatting rules).
3. Create the corresponding Agent Skills configuration files (e.g., in a `.jules/skills` directory or similar, as per the specification).
4. Provide a brief explanation of what each skill does and why it is useful for this repository."""

    # 3. Create a new Jules session
    session = await jules.session(
        prompt=prompt,
        source={
            "github": f"{owner}/{repo}",
            "baseBranch": base_branch
        },
        autoPr=True
    )

    print(f"Session created successfully. ID: {session.id}")

    # 4. Monitor the progress
    async for activity in session.stream():
        if activity.type == "planGenerated":
            print(f"[Plan Generated] {len(activity.plan.steps)} steps.")
        elif activity.type == "progressUpdated":
            print(f"[Progress Updated] {activity.title}")
        elif activity.type == "sessionCompleted":
            print("[Session Completed]")

    # 5. Wait for the final outcome
    outcome = await session.result()

    if outcome.state == "failed":
        print("::error::Session failed.")
        sys.exit(1)

    print("Session finished successfully.")

    if getattr(outcome, "pullRequest", None):
        print(f"Pull Request created: {outcome.pullRequest.url}")

if __name__ == "__main__":
    asyncio.run(run())
