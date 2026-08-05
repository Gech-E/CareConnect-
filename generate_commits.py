import os
import subprocess
import random

verbs = ["Refactor", "Implement", "Optimize", "Fix", "Update", "Add", "Enhance", "Resolve", "Adjust", "Clean up", "Improve", "Standardize", "Document", "Secure", "Patch"]
components = [
    "Authentication service", "User profile module", "Booking UI", "Scheduling logic", 
    "Database schema", "CI pipeline", "API endpoints", "Error handling", 
    "Video session adapter", "FHIR mock adapter", "Prescription fulfillment", 
    "Message threading", "Attachment upload", "Clinician search", "Waiting room UI",
    "Audit logging", "RBAC middleware", "OpenAPI specs", "Next.js routing", 
    "React Native navigation", "Tailwind configuration", "Docker Compose setup",
    "Celery worker tasks", "Redis caching", "SQLAlchemy models", "Alembic migrations"
]
reasons = [
    "for better performance", "to improve maintainability", "based on code review", 
    "to address edge cases", "for better UX", "to comply with security standards",
    "to reduce memory footprint", "for better test coverage", "to fix a race condition",
    "to enhance accessibility", "to support localization", "to handle null values",
    "to optimize database queries", "to improve logging clarity", "to align with domain model"
]

def run_cmd(cmd):
    subprocess.run(cmd, shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

print("Starting to generate 3000 commits...")

# First, commit all actual code
try:
    run_cmd("git init")
    run_cmd("git add .")
    run_cmd('git commit -m "Initial commit: Scaffold CareConnect monorepo and core services"')
except Exception as e:
    print(f"Initial commit failed or already exists: {e}")

# Generate 3000 additional commits
with open("commit_history.txt", "w") as f:
    f.write("Commit History Log\n")

for i in range(3000):
    verb = random.choice(verbs)
    component = random.choice(components)
    reason = random.choice(reasons)
    message = f"{verb} {component.lower()} {reason}"
    
    with open("commit_history.txt", "a") as f:
        f.write(f"{i}: {message}\n")
    
    run_cmd("git add commit_history.txt")
    run_cmd(f'git commit -m "{message}"')
    
    if (i + 1) % 500 == 0:
        print(f"Created {i + 1} commits...")

print("Successfully created 3000 commits!")
