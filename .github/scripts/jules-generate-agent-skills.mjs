import * as core from "@actions/core";
import * as github from "@actions/github";

let julesModule;
try {
  // Use dynamic import to safely resolve ESM packages and bypass strict CommonJS require() limits
  julesModule = await import("@google/jules-sdk");
} catch (err) {
  core.setFailed(`Failed to dynamically import @google/jules-sdk: ${err.message}`);
  process.exit(1);
}

const jules = julesModule.jules || julesModule.default?.jules || julesModule.default;

if (!jules) {
  core.setFailed("Could not extract the jules object from the SDK exports.");
  process.exit(1);
}

if (!process.env.JULES_API_KEY) {
  core.setFailed("JULES_API_KEY environment variable is missing.");
  process.exit(1);
}

const context = github.context;
const owner = context.repo.owner || process.env.GITHUB_REPOSITORY?.split("/")[0] || "unknown";
const repo = context.repo.repo || process.env.GITHUB_REPOSITORY?.split("/")[1] || "unknown";
const ref = context.ref || process.env.GITHUB_REF || "refs/heads/main";

let baseBranch = "main";

jules.configure({ apiKey: process.env.JULES_API_KEY });

if (ref.startsWith("refs/heads/")) baseBranch = ref.replace("refs/heads/", "");

core.info(`Starting Jules session for ${owner}/${repo} on branch ${baseBranch}`);

const prompt = `Analyze this repository and suggest Agent Skills to improve automation of common or complex tasks.

Use the Agent Skills specification located at https://agentskills.io/specification.md as a reference for formatting and structuring the skills.

Tasks:
1. Review the repository structure, code, and existing workflows.
2. Identify 1 to 3 areas where an Agent Skill could be beneficial (e.g., code review, automated testing, boilerplate generation, or specific formatting rules).
3. Create the corresponding Agent Skills configuration files (e.g., in a \`.jules/skills\` directory or similar, as per the specification).
4. Provide a brief explanation of what each skill does and why it is useful for this repository.`;

const session = await jules.session({
  apiKey: process.env.JULES_API_KEY,
  prompt,
  source: { github: `${owner}/${repo}`, baseBranch },
  autoPr: true,
});

core.info(`Session created successfully. ID: ${session.id}`);

for await (const activity of session.stream()) {
  if (activity.type === "planGenerated") core.info(`[Plan Generated] ${activity.plan.steps.length} steps.`);
  if (activity.type === "progressUpdated") core.info(`[Progress Updated] ${activity.title}`);
  if (activity.type === "sessionCompleted") core.info(`[Session Completed]`);
}

const outcome = await session.result();
if (outcome.state === "failed") {
  core.setFailed("Session failed.");
  process.exit(1);
}

core.info("Session finished successfully.");
if (outcome.pullRequest) {
  core.info(`Pull Request created: ${outcome.pullRequest.url}`);
}
