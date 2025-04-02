import os
import requests
import yaml
import tempfile
import subprocess
import shutil

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
HEADERS = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}

def load_config(path="config.yaml"):
    try:
        with open(path, "r") as f:
            print(f"📥 Loading config from `{path}`")
            return yaml.safe_load(f)
    except Exception as e:
        print(f"❌ Failed to load config file: {e}")
        exit(1)

def clone_repo_and_check_files(repo, files):
    temp_dir = tempfile.mkdtemp()
    repo_url = f"https://github.com/{repo}.git"
    file_status = {}

    try:
        print(f"🌀 Cloning {repo}...")
        subprocess.run(
            ["git", "clone", "--depth", "1", repo_url, temp_dir],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )

        for file in files:
            full_path = os.path.join(temp_dir, file)
            file_status[file] = os.path.exists(full_path)

    except subprocess.CalledProcessError:
        print(f"❌ Failed to clone {repo}")
        file_status = {file: False for file in files}
    finally:
        shutil.rmtree(temp_dir)

    return file_status

def list_workflows(repo):
    url = f"https://api.github.com/repos/{repo}/actions/workflows"
    try:
        resp = requests.get(url, headers=HEADERS)
        if resp.status_code != 200:
            print(f"⚠️ Could not fetch workflows for `{repo}` (status {resp.status_code})")
            return []
        return resp.json().get("workflows", [])
    except requests.RequestException as e:
        print(f"❌ Error fetching workflows for `{repo}`: {e}")
        return []

def get_workflow_run_status(repo, workflow_id):
    url = f"https://api.github.com/repos/{repo}/actions/workflows/{workflow_id}/runs?per_page=1"
    try:
        resp = requests.get(url, headers=HEADERS)
        if resp.status_code != 200:
            return "not run"
        runs = resp.json().get("workflow_runs", [])
        if not runs:
            return "not run"
        run = runs[0]
        if run["status"] == "completed":
            return run["conclusion"] or "completed"
        return run["status"]
    except requests.RequestException:
        return "error"

def check_workflows(repo, workflows):
    available = list_workflows(repo)
    results = {}

    for wf in workflows:
        wf_path = ".github/workflows/" + wf
        wf = next((w for w in available if w["path"] == wf_path), None)
        if not wf:
            results[wf_path] = "❌ missing"
        else:
            state = wf.get("state", "unknown")
            run_status = get_workflow_run_status(repo, wf["id"])
            if state == "active" and run_status == "success":
                results[wf_path] = "✅"
            else:
                results[wf_path] = f"❌ {state}, run: {run_status}"

    return results

def generate_markdown_report(config):
    report = []

    for repo_type, data in config.get("repo_types", {}).items():
        repos = data.get("repos", [])
        required_files = data.get("checks", {}).get("required_files", [])
        required_workflows = data.get("checks", {}).get("workflows", [])

        if not (required_files or required_workflows):
            print(f"⚠️ No checks defined for repo type `{repo_type}`. Skipping.")
            continue

        emoji = "📦"
        report.append(f"# {emoji} {repo_type.capitalize()} Repo Compliance Report\n")
        headers = ["Repository"] + required_files + required_workflows
        report.append("| " + " | ".join(headers) + " |")
        report.append("| " + " | ".join(["---"] * len(headers)) + " |")

        for repo in repos:
            print(f"🔍 Checking `{repo}`")
            row = [f"`{repo}`"]

            file_results = clone_repo_and_check_files(repo, required_files)
            for f in required_files:
                status = "✅" if file_results.get(f, False) else "❌"
                print(f"    📄 {f}: {status}")
                row.append(status)

            workflow_results = check_workflows(repo, required_workflows)
            for wf in required_workflows:
                status = workflow_results.get(".github/workflows/"+ wf, "❌ unknown")
                print(f"    ⚙️  {wf}: {status}")
                row.append(status)

            report.append("| " + " | ".join(row) + " |")

        report.append("")  # Spacer

    return report

def write_report(report, path="report.md"):
    try:
        with open(path, "w") as f:
            f.write("\n".join(report))
        print(f"\n✅ Report successfully written to `{path}`")
    except Exception as e:
        print(f"❌ Failed to write report: {e}")

if __name__ == "__main__":
    config = load_config()
    markdown = generate_markdown_report(config)
    write_report(markdown)
