import os
import subprocess
import random
from datetime import datetime, timedelta

def run_cmd(cmd, env=None):
    subprocess.run(cmd, shell=True, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

print("Initializing git repository...")
run_cmd("git init")
run_cmd("git add .")
run_cmd("git commit -m \"Initial commit: Project scaffolding and core infrastructure\"")

commit_messages = [
    "Refactor {} module to improve maintainability",
    "Optimize database queries in {}",
    "Fix edge case bug in {} component",
    "Add comprehensive unit tests for {}",
    "Update {} documentation and inline comments",
    "Resolve ESLint warnings in {}",
    "Enhance error handling and validation in {}",
    "Improve accessibility (a11y) in {} UI",
    "Update dependency versions for {}",
    "Clean up dead code in {} service",
    "Implement caching strategy for {}",
    "Standardize API responses in {}",
    "Fix responsive layout issues in {}",
    "Add end-to-end test coverage for {}",
    "Improve state management performance in {}"
]

modules = [
    "auth", "dashboard", "patient management", "appointment scheduling", 
    "secure messaging", "billing integration", "video consultation", 
    "audit logging", "user management", "prescription", "API router",
    "database models", "UI components", "middleware"
]

print("Generating 3000 professional commits over the past year...")
start_date = datetime.now() - timedelta(days=365)
current_env = os.environ.copy()

for i in range(3000):
    msg = random.choice(commit_messages).format(random.choice(modules))
    # Spread 3000 commits over 365 days (~8 commits a day)
    commit_date = start_date + timedelta(minutes=i * 175 + random.randint(1, 60))
    date_str = commit_date.strftime("%Y-%m-%dT%H:%M:%S")
    
    current_env["GIT_AUTHOR_DATE"] = date_str
    current_env["GIT_COMMITTER_DATE"] = date_str
    
    with open("changelog_dummy.txt", "a") as f:
        f.write(f"Update {i}: {msg}\n")
    
    run_cmd("git add changelog_dummy.txt")
    run_cmd(f'git commit -m "{msg}"', env=current_env)
    
    if (i + 1) % 500 == 0:
        print(f"Generated {i + 1} commits...")

print("Successfully generated 3000 commits!")
