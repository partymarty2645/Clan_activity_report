# ClanStats Implementation Rules & Guidelines

**Effective Date:** 2025-12-22  
**Status:** ACTIVE - All work must comply with these rules  
**Authority:** IMPLEMENTATION_PROGRESS.md (source of truth)

---

## 🚨 PRIMARY RULE

**ALL IMPLEMENTATION WORK MUST RESPECT THE IMPLEMENTATION_PROGRESS.MD FILE**

This is not a suggestion. This is the contract for this project. Every code change, every test, every decision must be traceable back to this file.

---

## 📋 Core Rules for All Sessions

### Rule 1: No Work Outside the Plan
- **Requirement:** Every task must be listed in IMPLEMENTATION_PROGRESS.md
- **Violation:** Creating files or modifying code not in the current phase
- **Consequence:** Commit will be rolled back, session reset
- **Exception:** Only bug fixes in already-implemented code are allowed

### Rule 2: Update Progress File FIRST
- **Requirement:** Before starting work, update the progress file
- **Action:** Change task status from ⬜ NOT STARTED to 🟠 IN PROGRESS
- **Format:** `- [x] **1.3.1 Create \`core/usernames.py\`**` (mark checkbox as done)
- **Timing:** BEFORE any code is written

### Rule 3: Complete One Full Task Before Moving On
- **Requirement:** Finish all sub-tasks of a task before marking complete
- **Sub-tasks Include:**
  - Code implementation (all files)
  - Tests written and passing
  - Validation checklist items verified
  - Documentation updated
- **Blocker:** Cannot start next task until current is 100% done

### Rule 4: Validation Checklist is MANDATORY
- **Requirement:** Every task has a validation checklist
- **Action:** You must complete EVERY item in the checklist
- **Proof:** Show test output or verification before marking task done
- **No Shortcuts:** "Looks good" is not sufficient

### Rule 5: Context Window Management
- **Trigger:** When context approaches 80% (about 160k tokens used)
- **Action:** START A NEW CHAT SESSION
- **Before Leaving:**
  - Save all work (commit to git)
  - Update IMPLEMENTATION_PROGRESS.md with exact current status
  - Note any blockers in "Issues Encountered" section
  - Copy the "Session Handoff Template" info to progress file
- **When Resuming:**
  - First action: Read IMPLEMENTATION_PROGRESS.md
  - Search codebase for completed files
  - Resume from exact checkpoint marked in progress file

### Rule 6: Phases Are Sequential
- **Requirement:** Must complete Phase 1 before starting Phase 2
- **Definition of Complete:** All tasks marked ✅ with passing tests
- **No Parallel Work:** Cannot work on Phase 2 while Phase 1 incomplete
- **Exception:** Documentation can be written ahead (doesn't count as "work")

### Rule 7: Testing is Not Optional
- **Requirement:** Every new file/function must have tests
- **Minimum:** 1 test per public function
- **Coverage:** `pytest --cov=<module>` must show 80%+ coverage
- **Passing:** All tests must pass before marking task done
- **Command:** `pytest tests/ -v` before ANY commit

### Rule 8: No Breaking Changes
- **Requirement:** Existing functionality must not break
- **Validation:** All old tests must still pass
- **Deprecation:** Old functions get deprecation wrapper, not deletion
- **Backward Compatibility:** New code must work alongside old code

### Rule 9: Database Changes Require Backup
- **Requirement:** Before ANY database schema change, create backup
- **Backup Command:** `python scripts/backup_db.py`
- **Verification:** Restore from backup to verify it works
- **Location:** `backups/clan_data_YYYYMMDD_HHMMSS.db`
- **Blocker:** Cannot run migration without valid backup

### Rule 10: Commit Frequently with Clear Messages
- **Frequency:** Every completed task = 1 commit
- **Format:** `git commit -m "Phase N.M.N: [Issue#] [Task Name] - [What Changed]"`
- **Example:** `git commit -m "Phase 1.3.1: Issue#3 Username Normalization - Added UsernameNormalizer class"`
- **Verification:** `git log --oneline` shows clear progression

---

## 🎯 Phase-Specific Rules

### Phase 1 Rules (Foundation)

**Goal:** Establish single sources of truth for configuration, usernames, and roles

- **Rule 1.1:** `core/usernames.py` is the ONLY place to normalize usernames
  - All scripts must import from this module
  - Old functions must show deprecation warnings
  - Validation: Search codebase for `normalize_user_string` - should only exist in utils.py as wrapper

- **Rule 1.2:** `core/roles.py` is the ONLY place to define clan roles
  - ClanRole Enum is authoritative
  - No hardcoded role lists remain in other files
  - Validation: Search codebase for `TIER_1_ROLES` - should not exist

- **Rule 1.3:** `core/config.py` must validate at startup
  - Config.fail_fast() called in main.py
  - All critical keys checked
  - Clear error messages for missing configs

- **Rule 1.4:** Test infrastructure is COMPLETE before Phase 2 starts
  - conftest.py exists with all fixtures
  - mocks.py has MockWOMClient and MockDiscordService
  - pytest --collect-only shows all tests discovered

### Phase 2 Rules (Core Architecture)

**Goal:** Decouple API clients and refactor database

- **Rule 2.1:** ServiceFactory is the ONLY way to get API clients
  - No direct imports of wom_client or discord_service
  - Dependency injection pattern enforced
  - Tests can inject mocks

- **Rule 2.2:** Database migration is HIGH RISK
  - Backup verified BEFORE any migration runs
  - Integrity tests pass after EACH migration
  - Rollback procedure tested
  - No partial migrations - all or nothing

- **Rule 2.3:** No queries use usernames as primary keys
  - All queries use user_id (integer)
  - Performance improvement validated
  - N+1 query pattern eliminated

### Phase 3 Rules (Polish & Scale)

**Goal:** Optimize, observe, and prepare for production

- **Rule 3.1:** All timestamps are UTC internally
  - TimestampHelper.to_utc() used for all input
  - Display formatting only at output
  - No timezone-aware calculations in DB queries

- **Rule 3.2:** Performance benchmarks are measurable
  - Report generation <2s (verified with time measurement)
  - Dashboard export <1s
  - No performance regressions

- **Rule 3.3:** Observability includes trace IDs
  - setup_observability() called in main.py
  - All logs include trace ID
  - Pipeline checkpoints logged

---

## 🔍 Enforcement Checklist (Before Every Commit)

Before committing ANY changes, run this checklist:

- [ ] Progress file updated - current task marked as ✅ DONE (checkbox checked)
- [ ] ALL sub-tasks completed - no "will do later"
- [ ] Validation checklist items verified - copy/paste test output if needed
- [ ] Tests pass - `pytest tests/ -v` shows no failures
- [ ] No import errors - `python -c "import core.usernames"` works
- [ ] No regressions - old tests still pass
- [ ] Code follows existing patterns in the codebase
- [ ] Git commit message is clear and references IMPLEMENTATION_PROGRESS.md
- [ ] Related files are mentioned in commit message
- [ ] Database backup created (if applicable)
- [ ] Progress file committed along with code changes

**If ANY checkbox fails:** Stop. Fix. Then commit.

---

## 🚫 Anti-Patterns (Never Do This)

### Anti-Pattern 1: Silent Failures
**Don't:** Run a test that fails, ignore it, commit anyway
**Do:** Fix the test, verify it passes, then commit

### Anti-Pattern 2: Partial Tasks
**Don't:** Implement code but skip tests, mark as "mostly done"
**Do:** Complete all code, tests, AND validation before moving on

### Anti-Pattern 3: Out-of-Order Work
**Don't:** Skip Issue #3 and start Issue #4 because it seems easier
**Do:** Follow the sequence in IMPLEMENTATION_PROGRESS.md exactly

### Anti-Pattern 4: Ignoring Blockers
**Don't:** "I'll work around this issue for now"
**Do:** Document in "Issues Encountered" section and solve it

### Anti-Pattern 5: Ambiguous Progress
**Don't:** Update progress file with vague descriptions
**Do:** Update with exact file names and specific changes

### Anti-Pattern 6: Working Offline
**Don't:** Make changes for 2 hours without updating progress file
**Do:** Update progress file every 30 minutes (saves context on crash)

### Anti-Pattern 7: Breaking Changes Without Notice
**Don't:** Delete a function that other code might use
**Do:** Add deprecation warning, verify no usage, then remove in next phase

---

## 📝 When to Update IMPLEMENTATION_PROGRESS.md

### Update BEFORE Starting Work
```
- [ ] **1.3.1 Create `core/usernames.py`**
  - File: `core/usernames.py`
  - Status: ⬜ NOT STARTED

→ CHANGE TO:

- [x] **1.3.1 Create `core/usernames.py`**
  - File: `core/usernames.py`
  - Status: 🟠 IN PROGRESS
```

### Update AFTER Completing Work
```
- [x] **1.3.1 Create `core/usernames.py`**
  - File: `core/usernames.py`
  - Status: 🟠 IN PROGRESS

↓ Add evidence:

#### Validation Completed
- [x] All tests pass: pytest tests/test_usernames.py -v (6 tests passed)
- [x] No import errors
- [x] Deprecation wrapper working (tested with old function)
- [x] All scripts updated: harvest_sqlite.py, report_sqlite.py

**Status:** ✅ COMPLETE
```

### Document Issues Immediately
```
### Issues Encountered

- **2025-12-23 10:30** - Issue#3: Unicode space handling
  - Problem: Non-breaking space (U+00A0) not being normalized
  - Solution: Added explicit handling in normalize() function
  - Verified: Test case test_normalize_unicode_spaces() now passes
  - Status: ✅ RESOLVED
```

---

## 🔗 Git Integration Rules

### Commit Format
```
<Phase.Issue.Task>: <Task Name> - <What Changed>

Body:
- Files created/modified: [list]
- Tests: [how many, pass/fail status]
- Related: [other issues/tasks]
- Blockers: [any outstanding issues]
```

### Example Commit
```
1.3.1: Issue#3 Username Normalization - Centralized username handling

Files created:
- core/usernames.py (UsernameNormalizer class)
- tests/test_usernames.py (6 test cases)

Files modified:
- core/utils.py (added deprecation wrapper)
- scripts/harvest_sqlite.py (updated to use new normalizer)
- scripts/report_sqlite.py (removed robust_norm function)

Tests: 6/6 passing
Validation: All items in checklist verified
Blockers: None
```

---

## ✅ Sign-Off Requirements

### To Mark a Task as COMPLETE:

You must provide:

1. **List of all files created** (with line counts)
2. **List of all files modified** (with changes summary)
3. **Test results** (paste actual pytest output)
4. **Validation evidence** (paste outputs or screenshots)
5. **No blockers or issues** (or document them clearly)

### Example Sign-Off:
```
TASK COMPLETE: Issue #3.1.1 - Create core/usernames.py

Files Created:
✅ core/usernames.py (165 lines)
✅ tests/test_usernames.py (94 lines)

Files Modified:
✅ core/utils.py (+12 lines, deprecation wrapper added)
✅ scripts/harvest_sqlite.py (+3 lines, import added)
✅ scripts/report_sqlite.py (-5 lines, robust_norm removed)

Test Results:
$ pytest tests/test_usernames.py -v
tests/test_usernames.py::TestUsernameNormalizer::test_normalize_spaces PASSED
tests/test_usernames.py::TestUsernameNormalizer::test_normalize_underscores_hyphens PASSED
tests/test_usernames.py::TestUsernameNormalizer::test_normalize_unicode_spaces PASSED
tests/test_usernames.py::TestUsernameNormalizer::test_normalize_empty_string PASSED
tests/test_usernames.py::TestUsernameNormalizer::test_are_same_user PASSED
tests/test_usernames.py::TestUsernameNormalizer::test_canonical PASSED

======================== 6 passed in 0.45s ========================

Validation Checklist:
✅ All tests pass
✅ No import errors
✅ Deprecation wrapper tested
✅ Backward compatible
✅ No regressions in existing tests

Status: ✅ READY FOR COMMIT
```

---

## 🚨 If Rules Are Broken

### Violation: Commit without updating progress file
**Consequence:** Commit must be reverted, work redone with proper tracking

### Violation: Work on multiple tasks simultaneously
**Consequence:** Session paused, focus on completing one task, then resume

### Violation: Breaking existing tests
**Consequence:** Fix must be committed before new work continues

### Violation: Database change without backup
**Consequence:** Work rolled back, backup created, retry from checkpoint

### Violation: Skipping validation checklist items
**Consequence:** Task marked incomplete, must redo checklist

---

## 📞 When In Doubt

1. **Check IMPLEMENTATION_PROGRESS.md** - Is this task listed?
2. **Check validation checklist** - Are all items completed?
3. **Run tests** - Do all tests pass?
4. **Search for existing code** - Is this pattern used elsewhere?
5. **If still unsure** - Mark progress file as "BLOCKED" and document the issue

---

## 🔄 Session Handoff Checklist

**BEFORE ending a session, check:**

- [ ] Current task status updated in IMPLEMENTATION_PROGRESS.md
- [ ] All work committed to git
- [ ] No uncommitted changes (`git status` shows clean)
- [ ] Issues Encountered section updated with any blockers
- [ ] Session Handoff Template section filled out
- [ ] Next immediate steps clearly marked

**Then paste into new session:**
```
I'm continuing ClanStats implementation from session N.

[PASTE Session Handoff Template from IMPLEMENTATION_PROGRESS.md]
```

---

## ✨ Success Criteria

You know you're following the rules when:

✅ IMPLEMENTATION_PROGRESS.md is always up-to-date (updated within last 30 minutes)  
✅ Every commit message references IMPLEMENTATION_PROGRESS.md task number  
✅ All tests pass (`pytest tests/ -v` shows no failures)  
✅ No task is in IN PROGRESS for more than 4 hours  
✅ Validation checklists are 100% complete before marking tasks done  
✅ Git log shows clear progression through phases  
✅ No ambiguity about current status (always clear what's being worked on)  

---

## 👨‍⚖️ Authority & Disputes

**Question:** What if I think a task should be different?  
**Answer:** Update the task in IMPLEMENTATION_PROGRESS.md, note the change in git commit message, continue work

**Question:** What if rules conflict?  
**Answer:** IMPLEMENTATION_PROGRESS.md is the source of truth. These rules serve it.

**Question:** What if I need to deviate from the plan?  
**Answer:** Document the deviation clearly in IMPLEMENTATION_PROGRESS.md "Issues Encountered" section with rationale

---

**Last Updated:** 2025-12-22  
**Enforced By:** VS Code settings + GitHub pre-commit hooks (optional)  
**Questions?:** See IMPLEMENTATION_PROGRESS.md "Support & Escalation" section

**REMEMBER:** This file and IMPLEMENTATION_PROGRESS.md are the law of this project. Everything else is optional.
