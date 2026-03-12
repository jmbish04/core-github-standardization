#!/usr/bin/env python3
"""
PR Docstring Generator

Loops over all open PRs in the repository, checks out each branch,
scans every added/modified file for missing or inadequate docstrings,
generates best-practice docstrings per language, and commits them
directly to the PR branch.

Dependencies:
    - PyGithub
    - git (CLI, available on GitHub Actions runners)
"""

import os
import re
import subprocess
import sys
from pathlib import Path

from github import Github

# ──────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────

SKIP_PATHS = {
    "node_modules", ".git", "dist", "build", ".next", "__pycache__",
    "package-lock.json", "pnpm-lock.yaml", "yarn.lock",
    ".env", ".DS_Store", "venv", ".venv",
}

# Extensions that cannot carry comments — always skip
SKIP_EXTENSIONS = {".json", ".md", ".png", ".jpg", ".svg", ".ico", ".woff", ".woff2", ".lock"}

# Language configs keyed by extension
LANG_CONFIG = {
    ".ts":    "typescript",
    ".tsx":   "typescript",
    ".js":    "javascript",
    ".jsx":   "javascript",
    ".mjs":   "javascript",
    ".astro": "astro",
    ".py":    "python",
    ".css":   "css",
    ".html":  "html",
    ".sh":    "shell",
    ".yaml":  "yaml",
    ".yml":   "yaml",
}

# Regex patterns that identify code blocks needing docstrings
CODE_BLOCK_PATTERNS = [
    # TypeScript / JavaScript
    re.compile(r"^(\s*)(export\s+)?(default\s+)?(async\s+)?function\s+(\w+)"),
    re.compile(r"^(\s*)(export\s+)?(default\s+)?class\s+(\w+)"),
    re.compile(r"^(\s*)(export\s+)?(default\s+)?interface\s+(\w+)"),
    re.compile(r"^(\s*)(export\s+)?(default\s+)?type\s+(\w+)"),
    re.compile(r"^(\s*)(export\s+)?const\s+(\w+)\s*[:=]\s*(async\s+)?\("),
    re.compile(r"^(\s*)(export\s+)?(const|let|var)\s+(\w+)\s*=\s*(async\s+)?(\([^)]*\)|[a-zA-Z_]\w*)\s*=>"),
    re.compile(r"^(\s*)(export\s+)?const\s+(\w+)\s*=\s*\{"),
    # Python
    re.compile(r"^(\s*)(async\s+)?def\s+(\w+)"),
    re.compile(r"^(\s*)class\s+(\w+)"),
    # Shell
    re.compile(r"^(\s*)(\w+)\s*\(\)\s*\{"),
    re.compile(r"^(\s*)function\s+(\w+)"),
]


# ──────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────

def run(cmd: str, check: bool = True) -> subprocess.CompletedProcess:
    """Run a shell command and return the CompletedProcess result.

    Args:
        cmd: Shell command string to execute.
        check: If True, raise on non-zero exit code.

    Returns:
        subprocess.CompletedProcess with captured stdout/stderr.
    """
    print(f"    $ {cmd}")
    return subprocess.run(
        cmd, shell=True, capture_output=True, text=True, check=check,
    )


def try_run(cmd: str) -> subprocess.CompletedProcess:
    """Run a shell command without raising on failure.

    Args:
        cmd: Shell command string to execute.

    Returns:
        subprocess.CompletedProcess (always succeeds at Python level).
    """
    return run(cmd, check=False)


def should_skip(filepath: str) -> bool:
    """Check whether a file path should be skipped.

    Args:
        filepath: Relative path to evaluate.

    Returns:
        True if the file should be skipped.
    """
    parts = Path(filepath).parts
    if any(skip in parts or skip == filepath for skip in SKIP_PATHS):
        return True
    ext = Path(filepath).suffix.lower()
    if ext in SKIP_EXTENSIONS:
        return True
    return ext not in LANG_CONFIG


# ──────────────────────────────────────────────────────────────
# Docstring detection
# ──────────────────────────────────────────────────────────────

def has_file_docstring(content: str, ext: str) -> bool:
    """Check whether a file already has an adequate file-level docstring.

    Args:
        content: Full file content as a string.
        ext: File extension including the dot (e.g. '.ts').

    Returns:
        True if a sufficient file-level docstring is present.
    """
    trimmed = content.lstrip()

    if ext in {".ts", ".tsx", ".js", ".jsx", ".mjs"}:
        m = re.match(r"^/\*\*([\s\S]*?)\*/", trimmed)
        if not m:
            return False
        body = m.group(1)
        tag_count = len(re.findall(r"@\w+", body))
        desc_lines = [
            l for l in body.split("\n")
            if len(l.strip().lstrip("* ")) > 10
        ]
        return tag_count >= 2 or len(desc_lines) >= 3

    if ext == ".py":
        m = re.match(r'^("""|\'\'\')', trimmed)
        if not m:
            return False
        q = m.group(1)
        end = trimmed.find(q, len(q))
        if end == -1:
            return False
        block = trimmed[: end + len(q)]
        return block.count("\n") >= 2

    if ext == ".astro":
        m = re.match(r"^---\s*\n\s*/\*\*([\s\S]*?)\*/\s*\n", trimmed)
        return bool(m) and m.group(1).count("\n") >= 2

    if ext in {".sh", ".yaml", ".yml"}:
        lines = trimmed.split("\n")
        comment_lines = 0
        for line in lines:
            if line.strip().startswith("#"):
                comment_lines += 1
            else:
                break
        return comment_lines >= 3

    if ext == ".css":
        return trimmed.startswith("/**")

    if ext == ".html":
        return trimmed.startswith("<!--")

    return True


def block_has_docstring(lines: list[str], idx: int) -> bool:
    """Check whether a code block already has a docstring above it.

    Args:
        lines: All lines of the file.
        idx: Line index of the code-block declaration.

    Returns:
        True if a comment/docstring is found directly above.
    """
    for i in range(idx - 1, max(-1, idx - 6), -1):
        stripped = lines[i].strip()
        if stripped == "":
            continue
        if any(stripped.startswith(p) or stripped.endswith(p) for p in (
            "*/", "/**", "* ", "//", "#", '"""', "'''"
        )):
            return True
        break
    return False


# ──────────────────────────────────────────────────────────────
# Docstring generation
# ──────────────────────────────────────────────────────────────

def infer_purpose(filepath: str) -> str:
    """Infer a short purpose description from the file path.

    Args:
        filepath: Relative file path.

    Returns:
        A human-readable purpose string.
    """
    name = Path(filepath).name
    parent = Path(filepath).parent.as_posix()

    mapping = [
        ("api",        f"API route handler: {name}"),
        ("route",      f"Route handler: {name}"),
        ("component",  f"UI component: {name}"),
        ("schema",     f"Database schema/model: {name}"),
        ("db",         f"Database module: {name}"),
        ("util",       f"Utility module: {name}"),
        ("lib",        f"Library module: {name}"),
        ("middleware",  f"Middleware: {name}"),
        ("config",     f"Configuration: {name}"),
        ("worker",     f"Cloudflare Worker entry: {name}"),
        ("migration",  f"Database migration: {name}"),
        ("page",       f"Page component: {name}"),
        ("layout",     f"Layout component: {name}"),
        ("hook",       f"Custom hook: {name}"),
        ("store",      f"State store: {name}"),
        ("test",       f"Test suite: {name}"),
        ("script",     f"Script: {name}"),
    ]

    for keyword, desc in mapping:
        if keyword in parent.lower() or keyword in name.lower():
            return desc
    return f"Module providing functionality for {name}"


def detect_cf_bindings(content: str) -> list[str]:
    """Detect Cloudflare binding usage in file content.

    Args:
        content: Full file content.

    Returns:
        List of detected Cloudflare binding descriptions.
    """
    bindings = []
    checks = [
        (["D1Database", ".d1"],    "D1 (SQL database)"),
        (["R2Bucket", ".r2"],      "R2 (object storage)"),
        (["KVNamespace", ".kv"],   "KV (key-value store)"),
        (["DurableObject"],        "Durable Objects"),
        (["AI", "ai.run"],         "Workers AI"),
    ]
    for keywords, label in checks:
        if any(kw in content for kw in keywords):
            bindings.append(label)
    return bindings


def detect_imports(content: str) -> list[str]:
    """Extract top import/require dependency names.

    Args:
        content: Full file content.

    Returns:
        Up to 5 dependency names.
    """
    matches = re.findall(r"""(?:import|require)\s.*?['"]([^'"]+)['"]""", content)
    return matches[:5]


def detect_zod_schemas(content: str) -> list[str]:
    """Detect Zod schema definitions.

    Args:
        content: Full file content.

    Returns:
        List of Zod schema definition lines.
    """
    return re.findall(r"(?:export\s+)?const\s+(\w+)\s*=\s*z\.\w+", content)


def generate_file_docstring(filepath: str, content: str, ext: str) -> str | None:
    """Generate a file-level docstring appropriate for the language.

    Args:
        filepath: Relative file path.
        content: Full file content.
        ext: File extension.

    Returns:
        Docstring string, or None if not applicable.
    """
    purpose = infer_purpose(filepath)
    deps = detect_imports(content)
    cf_bindings = detect_cf_bindings(content)
    zod_schemas = detect_zod_schemas(content)
    name_no_ext = Path(filepath).stem
    lines: list[str] = []

    if ext in {".ts", ".tsx", ".js", ".jsx", ".mjs"}:
        lines.append("/**")
        lines.append(f" * @fileoverview {purpose}")
        lines.append(" *")
        lines.append(f" * @module {name_no_ext}")
        if deps:
            lines.append(" *")
            lines.append(" * @dependencies")
            for d in deps:
                lines.append(f" *   - {d}")
        if cf_bindings:
            lines.append(" *")
            lines.append(" * @cloudflare-bindings")
            for b in cf_bindings:
                lines.append(f" *   - {b}")
        if zod_schemas:
            lines.append(" *")
            lines.append(f" * @schemas Defines {len(zod_schemas)} Zod validation schema(s)")
        lines.append(" */")

    elif ext == ".py":
        lines.append('"""')
        lines.append(purpose)
        lines.append("")
        if deps:
            lines.append("Dependencies:")
            for d in deps:
                lines.append(f"    - {d}")
            lines.append("")
        lines.append('"""')

    elif ext == ".astro":
        lines.append("/**")
        lines.append(f" * @component {name_no_ext}")
        lines.append(f" * @description {purpose}")
        if deps:
            lines.append(" *")
            lines.append(" * @dependencies")
            for d in deps:
                lines.append(f" *   - {d}")
        lines.append(" */")

    elif ext in {".sh"}:
        lines.append(f"# {'-' * 60}")
        lines.append(f"# {purpose}")
        lines.append(f"# {'-' * 60}")

    elif ext in {".yaml", ".yml"}:
        lines.append(f"# {'-' * 60}")
        lines.append(f"# {purpose}")
        lines.append(f"# {'-' * 60}")

    elif ext == ".css":
        lines.append("/**")
        lines.append(f" * {purpose}")
        lines.append(" */")

    elif ext == ".html":
        lines.append(f"<!-- {purpose} -->")

    return "\n".join(lines) if lines else None


def generate_block_docstring(line: str, indent: str, ext: str) -> str | None:
    """Generate a docstring for a code block (function, class, etc.).

    Args:
        line: The source line containing the declaration.
        indent: Whitespace indent of the declaration.
        ext: File extension.

    Returns:
        Docstring string, or None if not applicable.
    """
    parts: list[str] = []

    # Determine block type
    block_type = "function"
    func_name = ""
    is_async = "async" in line

    class_match = re.search(r"class\s+(\w+)", line)
    iface_match = re.search(r"interface\s+(\w+)", line)
    type_match = re.search(r"type\s+(\w+)", line)
    fn_match = re.search(r"(?:function\s+)?(\w+)\s*(?:[:=]\s*(?:async\s+)?)?\(", line)

    if class_match:
        func_name = class_match.group(1)
        block_type = "class"
    elif iface_match:
        func_name = iface_match.group(1)
        block_type = "interface"
    elif type_match:
        func_name = type_match.group(1)
        block_type = "type"
    elif fn_match:
        func_name = fn_match.group(1)

    # Extract params
    params: list[str] = []
    param_match = re.search(r"\(([^)]*)\)", line)
    if param_match and param_match.group(1).strip():
        raw = param_match.group(1).split(",")
        for p in raw:
            clean = p.strip()
            clean = re.sub(r"\s*[:=].*$", "", clean)
            clean = clean.lstrip(".")
            if clean:
                params.append(clean)

    type_labels = {
        "class": "Class",
        "interface": "Interface",
        "type": "Type definition for",
        "function": "Asynchronously handles" if is_async else "Handles",
    }

    if ext in {".ts", ".tsx", ".js", ".jsx", ".mjs"}:
        parts.append(f"{indent}/**")
        parts.append(f"{indent} * {type_labels.get(block_type, 'Handles')} {func_name or 'logic'}.")
        if block_type in {"function", "type"} and params:
            parts.append(f"{indent} *")
            for p in params:
                parts.append(f"{indent} * @param {p} - TODO: describe {p}")
        if block_type == "function":
            parts.append(f"{indent} * @returns TODO: describe return value")
            if is_async:
                parts.append(f"{indent} * @throws {{Error}} TODO: describe error conditions")
        parts.append(f"{indent} */")

    elif ext == ".py":
        parts.append(f'{indent}"""')
        parts.append(f"{indent}{func_name or 'Block'} — TODO: describe purpose.")
        if params:
            parts.append(f"{indent}")
            parts.append(f"{indent}Args:")
            for p in params:
                parts.append(f"{indent}    {p}: TODO: describe {p}")
        if block_type == "function":
            parts.append(f"{indent}")
            parts.append(f"{indent}Returns:")
            parts.append(f"{indent}    TODO: describe return value")
        parts.append(f'{indent}"""')

    elif ext == ".sh":
        parts.append(f"{indent}# {func_name or 'function'} — TODO: describe purpose")

    return "\n".join(parts) if parts else None


# ──────────────────────────────────────────────────────────────
# File processing
# ──────────────────────────────────────────────────────────────

def process_file(filepath: str, content: str) -> str | None:
    """Analyze a file and add missing docstrings.

    Args:
        filepath: Relative file path.
        content: Full file content.

    Returns:
        Updated content string if changes were made, else None.
    """
    ext = Path(filepath).suffix.lower()
    if ext not in LANG_CONFIG:
        return None

    modified = False
    lines = content.split("\n")

    # 1. File-level docstring
    if not has_file_docstring(content, ext):
        file_doc = generate_file_docstring(filepath, content, ext)
        if file_doc:
            if ext == ".astro":
                fm_idx = next(
                    (i for i, l in enumerate(lines) if l.strip() == "---"), -1
                )
                if fm_idx != -1:
                    lines.insert(fm_idx + 1, file_doc)
                else:
                    lines = ["---", file_doc, "---"] + lines
            elif ext == ".sh" and lines and lines[0].startswith("#!"):
                doc_lines = [
                    l for l in file_doc.split("\n") if not l.startswith("#!")
                ]
                for i, dl in enumerate(doc_lines):
                    lines.insert(1 + i, dl)
            else:
                lines = file_doc.split("\n") + [""] + lines
            modified = True
            print("      📝 Added file-level docstring")
    else:
        print("      ✔ File-level docstring already adequate")

    # 2. Code-block-level docstrings (collect then insert bottom-up)
    blocks_to_doc: list[dict] = []
    for i, line in enumerate(lines):
        for pattern in CODE_BLOCK_PATTERNS:
            if pattern.match(line):
                if not block_has_docstring(lines, i):
                    indent_match = re.match(r"^(\s*)", line)
                    indent = indent_match.group(1) if indent_match else ""
                    blocks_to_doc.append(
                        {"idx": i, "indent": indent, "line": line}
                    )
                break

    blocks_to_doc.reverse()
    for block in blocks_to_doc:
        doc = generate_block_docstring(block["line"], block["indent"], ext)
        if doc:
            doc_lines = doc.split("\n")
            for j, dl in enumerate(doc_lines):
                lines.insert(block["idx"] + j, dl)
            modified = True

    if blocks_to_doc:
        print(f"      📝 Added {len(blocks_to_doc)} code-block docstring(s)")
    else:
        print("      ✔ All code blocks already documented")

    return "\n".join(lines) if modified else None


# ──────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────

def main() -> None:
    """Entry point: iterate open PRs, generate docstrings, commit."""
    token = os.environ.get("GH_TOKEN")
    repository = os.environ.get("GITHUB_REPOSITORY")

    if not token or not repository:
        print("❌ Missing GH_TOKEN or GITHUB_REPOSITORY environment variable.")
        sys.exit(1)

    owner, repo = repository.split("/")
    g = Github(token)
    gh_repo = g.get_repo(repository)

    # Configure git
    run("git config user.name 'github-actions[bot]'")
    run("git config user.email 'github-actions[bot]@users.noreply.github.com'")

    print(f"\n{'═' * 60}")
    print(f"📚 PR DOCSTRING GENERATOR — {owner}/{repo}")
    print(f"{'═' * 60}\n")

    open_prs = list(gh_repo.get_pulls(state="open"))
    print(f"📋 Found {len(open_prs)} open PR(s).\n")

    if not open_prs:
        print("✅ No open PRs. Nothing to document.")
        return

    results: list[dict] = []

    for pr in open_prs:
        print(f"\n{'─' * 60}")
        print(f"🔍 PR #{pr.number}: \"{pr.title}\"")
        print(f"   Branch: {pr.head.ref} → {pr.base.ref}")
        print(f"   Author: {pr.user.login}")
        print(f"{'─' * 60}\n")

        try:
            # Get changed files
            changed_files = list(pr.get_files())
            target_files = [
                f for f in changed_files
                if f.status in {"added", "modified"} and not should_skip(f.filename)
            ]

            print(f"   📄 {len(target_files)} documentable file(s) in this PR.\n")

            if not target_files:
                print("   ⏭ No documentable files. Skipping.\n")
                results.append({
                    "number": pr.number, "title": pr.title,
                    "status": "skipped", "reason": "no files", "files": 0,
                })
                continue

            # Checkout the PR branch
            run(f"git fetch origin {pr.head.ref}")
            check = try_run(f"git rev-parse --verify {pr.head.ref}")
            if check.returncode == 0:
                run(f"git checkout {pr.head.ref}")
                run(f"git reset --hard origin/{pr.head.ref}")
            else:
                run(f"git checkout -b {pr.head.ref} origin/{pr.head.ref}")

            files_updated = 0

            for f in target_files:
                filepath = f.filename
                full_path = Path(filepath)

                print(f"\n    📄 Processing: {filepath}")

                if not full_path.exists():
                    print("      ⚠ File not found on disk. Skipping.")
                    continue

                content = full_path.read_text(encoding="utf-8", errors="replace")
                updated = process_file(filepath, content)

                if updated is not None:
                    full_path.write_text(updated, encoding="utf-8")
                    run(f'git add "{filepath}"')
                    files_updated += 1
                    print("      ✅ Docstrings generated and staged.")
                else:
                    print("      ✔ Already fully documented. No changes.")

            # Commit and push
            if files_updated > 0:
                msg = (
                    f"docs: auto-generate docstrings for {files_updated} file(s)\n\n"
                    "Generated by PR Docstring Generator workflow.\n"
                    "Best-practice JSDoc/TSDoc/language-appropriate docstrings added\n"
                    "for file-level and code-block-level documentation."
                )
                run(f'git commit -m "{msg}"')
                run(f"git push origin {pr.head.ref}")
                print(f"\n    🚀 Pushed docstring updates to PR #{pr.number} ({files_updated} file(s)).")
                results.append({
                    "number": pr.number, "title": pr.title,
                    "status": "success", "files": files_updated,
                })
            else:
                print(f"\n    ✔ All files in PR #{pr.number} already documented. No commit needed.")
                results.append({
                    "number": pr.number, "title": pr.title,
                    "status": "skipped", "reason": "all documented", "files": 0,
                })

        except Exception as exc:
            print(f"\n    ❌ FAILED processing PR #{pr.number}: {exc}")
            results.append({
                "number": pr.number, "title": pr.title,
                "status": "failed", "error": str(exc), "files": 0,
            })
            try_run("git merge --abort")
            try_run("git checkout main")
            try_run("git reset --hard origin/main")

    # ── Summary ──
    print(f"\n\n{'═' * 60}")
    print(f"📊 DOCSTRING GENERATION SUMMARY — {owner}/{repo}")
    print(f"{'═' * 60}\n")

    succeeded = [r for r in results if r["status"] == "success"]
    skipped = [r for r in results if r["status"] == "skipped"]
    failed = [r for r in results if r["status"] == "failed"]

    for r in results:
        icon = {"success": "✅", "skipped": "⏭", "failed": "❌"}.get(r["status"], "?")
        print(f"  {icon} PR #{r['number']} — \"{r['title']}\" → {r['status'].upper()}")
        if r.get("files", 0) > 0:
            print(f"      └─ {r['files']} file(s) updated")
        if r.get("reason"):
            print(f"      └─ Reason: {r['reason']}")
        if r.get("error"):
            print(f"      └─ Error: {r['error']}")

    print(f"\n{'─' * 60}")
    print(f"  Total PRs processed : {len(results)}")
    print(f"  Docs generated      : {len(succeeded)}")
    print(f"  Already documented  : {len(skipped)}")
    print(f"  Failed              : {len(failed)}")
    print(f"{'─' * 60}\n")

    if not failed:
        print("🎉 All PRs have been analyzed and documented successfully!")
    else:
        print(f"⚠️  {len(failed)} PR(s) encountered errors. Review above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
