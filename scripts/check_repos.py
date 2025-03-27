import os
import subprocess
import shutil

REPOS_FILE = "repos.txt"
REQUIRED_FILES = ["README.md", "SECURITY.md", "LICENSE"]
CLONE_DIR = "temp_repos"
RESULT_FILE = "results.md"

def clone_repo(repo):
    url = f"https://github.com/{repo}.git"
    local_path = os.path.join(CLONE_DIR, repo.replace("/", "_"))
    try:
        subprocess.run(["git", "clone", "--depth=1", url, local_path],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return local_path
    except subprocess.CalledProcessError:
        print(f"❌ Failed to clone {repo}")
        return None

def is_golang_repo(path):
    for root, _, files in os.walk(path):
        for file in files:
            if file.endswith(".go") or file == "go.mod":
                return True
    return False

def check_required_files(path):
    found = {file: False for file in REQUIRED_FILES}
    for root, _, files in os.walk(path):
        for req_file in REQUIRED_FILES:
            if req_file in files:
                found[req_file] = True
    return found

def check_repo(repo):
    print(f"\n🔍 Checking {repo}...")
    local_path = clone_repo(repo)
    if not local_path:
        return None

    if not is_golang_repo(local_path):
        print(f"⏩ Skipping {repo} (not a Go repo)")
        shutil.rmtree(local_path, ignore_errors=True)
        return None

    print(f"✅ {repo} is a Go repository")
    result = check_required_files(local_path)
    shutil.rmtree(local_path, ignore_errors=True)

    return {"repo": repo, **result}

def write_results_markdown(results):
    with open(RESULT_FILE, "w") as f:
        f.write("# 🧪 Go Repo Compliance Report\n\n")
        f.write("| Repository | README.md | SECURITY.md | LICENSE |\n")
        f.write("|------------|------------|--------------|---------|\n")
        for r in results:
            f.write(f"| `{r['repo']}` "
                    f"| {'✅' if r.get('README.md') else '❌'} "
                    f"| {'✅' if r.get('SECURITY.md') else '❌'} "
                    f"| {'✅' if r.get('LICENSE') else '❌'} |\n")

def main():
    if not os.path.exists(REPOS_FILE):
        print(f"❌ Error: {REPOS_FILE} not found.")
        return

    os.makedirs(CLONE_DIR, exist_ok=True)

    with open(REPOS_FILE, "r") as f:
        repos = [line.strip() for line in f if line.strip()]

    results = []
    for repo in repos:
        result = check_repo(repo)
        if result:
            results.append(result)

    write_results_markdown(results)
    print(f"\n✅ Report written to `{RESULT_FILE}`")

    shutil.rmtree(CLONE_DIR, ignore_errors=True)

if __name__ == "__main__":
    main()
