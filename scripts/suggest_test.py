#!/usr/bin/env python3
import os
import subprocess
import re
import sys

import openai
from github import Github

def run_cmd(cmd):
    """Run a shell command and return its stdout, or exit on error."""
    try:
        return subprocess.check_output(cmd, stderr=subprocess.STDOUT).decode()
    except subprocess.CalledProcessError as e:
        print(f"Command {cmd!r} failed:\n{e.output.decode()}", file=sys.stderr)
        sys.exit(1)

def get_pr_number():
    """
    Extract PR number from GITHUB_REF, which is like 'refs/pull/42/merge'
    """
    ref = os.getenv("GITHUB_REF", "")
    parts = ref.split("/")
    if len(parts) >= 3 and parts[1] == "pull":
        return int(parts[2])
    print(f"Unexpected GITHUB_REF format: {ref}", file=sys.stderr)
    sys.exit(1)

def get_changed_go_functions():
    # Ensure we have the base branch to diff against
    run_cmd(["git", "fetch", "origin", "main", "--depth=1"])
    diff = run_cmd(["git", "diff", "origin/main...HEAD"])

    # Regex to capture full Go function bodies
    pattern = re.compile(
        r"func\s+\(?.*?\)?\s+\w+\([^)]*\)\s*\{[\s\S]+?\}",
        flags=re.MULTILINE | re.DOTALL
    )

    functions = []
    for match in pattern.finditer(diff):
        # Determine which file this chunk belongs to
        # (for simplicity, we'll comment them all under one header)
        functions.append(match.group(0).strip())
    return functions

def make_prompt(fn_code):
    return (
        "You are a Go testing assistant. Given this Go function, generate a Go "
        "table-driven test (using the testing package) that covers edge cases, "
        "error conditions, and all logical branches. Only return valid Go code.\n\n"
        "```go\n"
        f"{fn_code}\n"
        "```"
    )

def suggest_tests(functions):
    openai.api_key = os.getenv("OPENAI_API_KEY")
    suggestions = []
    for fn in functions:
        resp = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": make_prompt(fn)}],
            temperature=0.3
        )
        suggestions.append((fn, resp.choices[0].message.content.strip()))
    return suggestions

def post_comment(suggestions):
    gh = Github(os.getenv("GITHUB_TOKEN"))
    repo = gh.get_repo(os.getenv("GITHUB_REPOSITORY"))
    pr_number = get_pr_number()
    pr = repo.get_pull(pr_number)

    body = ["🧪 **Suggested Test Cases for Changed Go Functions**\n"]
    for fn, test_code in suggestions:
        body.append("### Function\n```go\n" + fn + "\n```\n")
        body.append(test_code + "\n")
    pr.create_issue_comment("\n".join(body))
    print(f"✅ Posted suggestions to PR #{pr_number}")

def main():
    funcs = get_changed_go_functions()
    if not funcs:
        print("✅ No changed Go functions detected.")
        return
    suggestions = suggest_tests(funcs)
    post_comment(suggestions)

if __name__ == "__main__":
    main()
