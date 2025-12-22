#!/usr/bin/env python
"""
IMPLEMENTATION_PROGRESS Monitor
Validates that the implementation is following rules and making progress.
Run this before every commit: python check_implementation_status.py
"""

import os
import re
import sys
from pathlib import Path
from datetime import datetime

def check_progress_file_exists():
    """Verify IMPLEMENTATION_PROGRESS.md exists and is readable."""
    if not Path("IMPLEMENTATION_PROGRESS.md").exists():
        return False, "IMPLEMENTATION_PROGRESS.md not found"
    return True, "Progress file exists"

def check_progress_file_updated():
    """Check if progress file was updated recently."""
    progress_file = Path("IMPLEMENTATION_PROGRESS.md")
    if not progress_file.exists():
        return False, "Progress file missing"
    
    mtime = os.path.getmtime(progress_file)
    now = datetime.now().timestamp()
    minutes_ago = (now - mtime) / 60
    
    if minutes_ago > 120:  # More than 2 hours
        return False, f"Progress file not updated for {int(minutes_ago)} minutes (limit: 120)"
    return True, f"Progress file updated {int(minutes_ago)} minutes ago"

def check_git_status_clean():
    """Verify no uncommitted changes exist (ready to commit)."""
    result = os.popen('git status --short').read().strip()
    if result:
        lines = result.split('\n')
        return False, f"Uncommitted changes: {len(lines)} files"
    return True, "Git status clean"

def check_tests_pass():
    """Verify all tests pass, preferring project venv if available."""
    # Prefer workspace venv python on Windows
    venv_python = Path('.venv') / 'Scripts' / 'python.exe'
    if venv_python.exists():
        cmd = f'"{venv_python}" -m pytest tests/ -q 2>&1'
    else:
        cmd = 'python -m pytest tests/ -q 2>&1'

    result = os.popen(cmd).read()
    lowered = result.lower()
    if 'failed' in lowered or 'error' in lowered:
        return False, "Tests are failing - fix before commit"
    if 'passed' in lowered:
        return True, "All tests passing"
    return False, "Cannot determine test status"

def check_current_task_in_progress():
    """Verify a task is marked as IN PROGRESS."""
    with open("IMPLEMENTATION_PROGRESS.md") as f:
        content = f.read()
    
    # Look for 🟠 IN PROGRESS
    if "🟠 IN PROGRESS" in content:
        # Extract task name
        match = re.search(r'\*\*([^*]+)\*\*[^*]*🟠 IN PROGRESS', content)
        if match:
            return True, f"Current task: {match.group(1)}"
    return False, "No task marked as IN PROGRESS"

def check_rules_file_exists():
    """Verify IMPLEMENTATION_RULES.md exists."""
    if Path("IMPLEMENTATION_RULES.md").exists():
        return True, "Rules file exists"
    return False, "IMPLEMENTATION_RULES.md missing"

def check_vs_code_config():
    """Verify VS Code configuration files exist."""
    configs = {
        ".vscode/settings.json": "settings",
        ".vscode/tasks.json": "tasks",
        ".vscode/launch.json": "launch"
    }
    
    missing = [name for path, name in configs.items() if not Path(path).exists()]
    if missing:
        return False, f"Missing VS Code configs: {', '.join(missing)}"
    return True, "All VS Code configs present"

def main():
    """Run all checks and report status."""
    print("\n" + "="*60)
    print("  IMPLEMENTATION STATUS CHECK")
    print("="*60 + "\n")
    
    checks = [
        ("Progress File", check_progress_file_exists),
        ("Progress Updated", check_progress_file_updated),
        ("Git Clean", check_git_status_clean),
        ("Tests Passing", check_tests_pass),
        ("Current Task", check_current_task_in_progress),
        ("Rules File", check_rules_file_exists),
        ("VS Code Config", check_vs_code_config),
    ]
    
    results = []
    for name, check_fn in checks:
        try:
            passed, message = check_fn()
            status = "✅ PASS" if passed else "❌ FAIL"
            results.append((passed, name, status, message))
            print(f"{status} | {name:20} | {message}")
        except Exception as e:
            results.append((False, name, "❌ ERROR", str(e)))
            print(f"❌ ERROR | {name:20} | {str(e)}")
    
    print("\n" + "="*60)
    
    passed_count = sum(1 for passed, _, _, _ in results if passed)
    total_count = len(results)
    
    print(f"\nSummary: {passed_count}/{total_count} checks passed\n")
    
    if passed_count == total_count:
        print("✅ ALL CHECKS PASSED - Ready for commit!")
        print("\nNext steps:")
        print("  1. git add .")
        print("  2. git commit -m 'Phase.Issue.Task: Name - Details'")
        print("  3. Update IMPLEMENTATION_PROGRESS.md with task as DONE")
        return 0
    else:
        print("❌ SOME CHECKS FAILED - Fix issues before commit")
        print("\nFailed checks:")
        for passed, name, status, message in results:
            if not passed:
                print(f"  - {name}: {message}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
