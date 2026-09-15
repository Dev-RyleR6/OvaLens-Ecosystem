#!/usr/bin/env python
"""
verify_and_commit.py — OvaLens Quality Gate & Automated Git Commit Utility

Usage:
    python scripts/verify_and_commit.py --type feat --scope backend --msg "add economic penoy yield calculation"
    python scripts/verify_and_commit.py -m "feat(backend): add economic penoy yield calculation" [--skip-frontend]
"""

import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
import os
import re
import subprocess
import argparse
from datetime import datetime

VALID_TYPES = ["feat", "fix", "refactor", "perf", "docs", "test", "chore"]
VALID_SCOPES = ["backend", "edge", "dashboard", "firmware", "docs", "agents", "ci", "repo", "architecture"]

def run_command(cmd, cwd=None, exit_on_fail=True):
    print(f"\n[RUNNING] {cmd} (cwd: {cwd or '.'})")
    res = subprocess.run(cmd, shell=True, cwd=cwd)
    if res.returncode != 0 and exit_on_fail:
        print(f"\n❌ FAILED: {cmd} exited with return code {res.returncode}")
        sys.exit(res.returncode)
    return res.returncode

def parse_commit_message(args):
    if args.message:
        pattern = r"^(feat|fix|refactor|perf|docs|test|chore)\(([a-z0-9_-]+)\):\s*(.+)$"
        m = re.match(pattern, args.message.strip())
        if not m:
            print("\n❌ Invalid commit message format!")
            print("Must follow Conventional Commits: <type>(<scope>): <subject>")
            print(f"Example: feat(backend): add penoy yield calculation")
            sys.exit(1)
        commit_type, commit_scope, commit_subject = m.groups()
    else:
        if not args.type or not args.scope or not args.msg:
            print("\n❌ Either --message (-m) OR (--type, --scope, --msg) must be provided!")
            sys.exit(1)
        commit_type = args.type.lower()
        commit_scope = args.scope.lower()
        commit_subject = args.msg.strip()

    if commit_type not in VALID_TYPES:
        print(f"\n❌ Invalid type '{commit_type}'. Must be one of: {', '.join(VALID_TYPES)}")
        sys.exit(1)

    full_message = f"{commit_type}({commit_scope}): {commit_subject}"
    return commit_type, commit_scope, commit_subject, full_message

def update_changelog(repo_root, commit_type, commit_scope, commit_subject):
    changelog_path = os.path.join(repo_root, "CHANGELOG.md")
    if not os.path.exists(changelog_path):
        return

    type_mapping = {
        "feat": "Added",
        "fix": "Fixed",
        "perf": "Changed",
        "refactor": "Changed",
        "docs": "Added",
        "chore": "Changed",
        "test": "Added"
    }
    section_name = type_mapping.get(commit_type, "Changed")
    entry = f"- **{commit_scope.capitalize()}**: {commit_subject} ({datetime.now().strftime('%Y-%m-%d')})"

    with open(changelog_path, "r", encoding="utf-8") as f:
        content = f.read()

    target_heading = f"### {section_name}"
    if target_heading in content:
        # Insert under the section heading
        replacement = f"{target_heading}\n{entry}"
        content = content.replace(target_heading, replacement, 1)
        with open(changelog_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"📝 Updated CHANGELOG.md under [{section_name}]")

def main():
    parser = argparse.ArgumentParser(description="OvaLens Automated Verification and Commit Tool")
    parser.add_argument("-m", "--message", help="Full commit message: <type>(<scope>): <subject>")
    parser.add_argument("--type", choices=VALID_TYPES, help="Commit type")
    parser.add_argument("--scope", help="Subsystem scope")
    parser.add_argument("--msg", help="Commit subject line")
    parser.add_argument("--skip-tests", action="store_true", help="Skip running test suites (not recommended)")
    parser.add_argument("--skip-frontend", action="store_true", help="Skip frontend build check")
    parser.add_argument("--no-changelog", action="store_true", help="Skip updating CHANGELOG.md")
    args = parser.parse_args()

    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    commit_type, commit_scope, commit_subject, full_message = parse_commit_message(args)

    print("=" * 70)
    print(f"🚀 OvaLens Automated Verification Gatekeeper")
    print(f"Commit: {full_message}")
    print("=" * 70)

    if not args.skip_tests:
        print("\n🧪 [1/3] Running Backend API Test Suite...")
        run_command(f"{sys.executable} -m pytest tests/test_api.py -v", cwd=os.path.join(repo_root, "backend"))

        print("\n🧪 [2/3] Running Edge CV Pipeline Test Suite...")
        run_command(f"{sys.executable} -m pytest tests/test_edge_pipeline.py -v", cwd=os.path.join(repo_root, "edge"))

        if not args.skip_frontend:
            print("\n🧪 [3/3] Checking React Dashboard Build...")
            run_command("npm.cmd run build", cwd=os.path.join(repo_root, "dashboard"))
    else:
        print("\n⚠️ Skipping automated test suites as requested.")

    # Update Changelog
    if not args.no_changelog:
        update_changelog(repo_root, commit_type, commit_scope, commit_subject)

    # Git stage and commit
    print("\n📦 Staging files and creating Git commit...")
    run_command("git add .", cwd=repo_root)
    run_command(f'git commit -m "{full_message}"', cwd=repo_root)

    print("\n" + "=" * 70)
    print(f"✅ SUCCESS: Verified and committed: {full_message}")
    print("=" * 70)

if __name__ == "__main__":
    main()
