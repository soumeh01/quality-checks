import os
import subprocess
import shutil

REPOS_FILE = "repos.txt"
REQUIRED_FILES = ["README.md", "SECURITY.md", "LICENSE"]
CLONE_DIR = "temp_repos"

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
    # Simple heuristic: presence of .go files or go.mod
    for root, _, files in os.walk(path):
        for file in files:
            if file.endswith(".go") or file == "go.mod":
                return True
    return False

def check_required_files(path):
    found = {}
    for req_file in REQUIRED_FILES:
        found[req_file] = False
        for root, _, files in os.walk(path):
            if req_file in files:
                found[req_file] = True
                break
    return found

def check_repo(repo):
    print(f"\n🔍 Checking {repo}...")
    local_path = clone_repo(repo)
    if not local_path:
        return

    if is_golang_repo(local_path):
        print(f"✅ {repo} is a Go repository")
        result = check_required_files(local_path)
        for file, exists in result.items():
            print(f"   - {file}: {'✅ Found' if exists else '❌ Missing'}")
    else:
        print(f"⏩ {repo} is not a Go repository")

    # Cleanup
    shutil.rmtree(local_path, ignore_errors=True)

def main():
    if not os.path.exists(REPOS_FILE):
        print(f"❌ Error: {REPOS_FILE} not found.")
        return

    os.makedirs(CLONE_DIR, exist_ok=True)

    with open(REPOS_FILE, "r") as f:
        repos = [line.strip() for line in f if line.strip()]

    for repo in repos:
        check_repo(repo)

    shutil.rmtree(CLONE_DIR, ignore_errors=True)

if __name__ == "__main__":
    main()
