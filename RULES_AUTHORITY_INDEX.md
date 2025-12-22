# ClanStats Implementation Authority & Rules Index

**Created:** 2025-12-22  
**Status:** ACTIVE - All governance in place  
**Authority:** These files form the complete framework for implementation

---

## 📚 The Five Pillar System

Your implementation follows a hierarchy of documents, each serving a specific purpose:

### PILLAR 1: Source of Truth
**File:** `IMPLEMENTATION_PROGRESS.md`  
**Purpose:** Single point of authority for what to do and what's complete  
**Updated:** Every 30 minutes during work  
**Authority Level:** 🔴 ABSOLUTE

**What it contains:**
- Current phase status
- All tasks with status (⬜ / 🟠 / ✅)
- Validation checklists for each task
- Evidence of completion (test outputs)
- Issues encountered log
- Session handoff template

**When to consult:** Before starting ANY work, to identify current task

---

### PILLAR 2: Rules & Enforcement
**File:** `IMPLEMENTATION_RULES.md`  
**Purpose:** Non-negotiable rules that govern how work is done  
**Review:** Start of every session  
**Authority Level:** 🔴 HIGH (violations block progress)

**What it contains:**
- 10 core rules (every work session must follow these)
- Phase-specific rules (extra rules for each phase)
- Anti-patterns to avoid
- Sign-off requirements for task completion
- Enforcement mechanisms

**When to consult:** When unsure if something is allowed, or before committing

---

### PILLAR 3: Workflow Guide
**File:** `VS_CODE_WORKFLOW.md`  
**Purpose:** Step-by-step procedures for daily work  
**Reference:** Throughout work session  
**Authority Level:** 🟡 MEDIUM (procedural, not enforceable)

**What it contains:**
- Session startup checklist
- Periodic (every 30min) actions
- Task completion procedures
- Testing commands
- Emergency procedures
- Pro tips for efficient work

**When to consult:** When you need instructions on HOW to do something

---

### PILLAR 4: Quick Reference
**File:** `QUICK_REFERENCE.md`  
**Purpose:** Fast command/syntax lookup  
**Access:** Keep in terminal/editor tab  
**Authority Level:** 🟡 LOW (reference only)

**What it contains:**
- Command shortcuts
- Test runners (one-liners)
- Git commands
- Status checkers
- Pre-commit checklist

**When to consult:** When you need syntax for a command

---

### PILLAR 5: Validation System
**File:** `check_implementation_status.py`  
**Purpose:** Automated checks before commit  
**Run:** Before every commit  
**Authority Level:** 🟢 ENFORCES (blocks bad commits)

**What it checks:**
- Progress file exists and is recent (updated <2 hours ago)
- Git status is clean (no uncommitted work)
- All tests pass
- Current task is marked IN PROGRESS
- Rules file exists
- VS Code config is complete

**Exit codes:**
- 0 = Ready to commit ✅
- 1 = Fix issues first ❌

---

## 🎯 Decision Tree: Which File Do I Need?

```
"What should I work on next?"
└─→ IMPLEMENTATION_PROGRESS.md (find current phase, next ⬜ task)

"How do I do this task?"
└─→ VS_CODE_WORKFLOW.md (step-by-step procedures)

"Is this allowed?"
└─→ IMPLEMENTATION_RULES.md (check the rules)

"What's the command for...?"
└─→ QUICK_REFERENCE.md (command syntax)

"Am I ready to commit?"
└─→ check_implementation_status.py (must pass all checks)

"Can I do X?"
└─→ Check IMPLEMENTATION_PROGRESS.md - if task not listed, answer is NO
```

---

## 🚀 Implementation Phases

Each phase is clearly defined in IMPLEMENTATION_PROGRESS.md with:
- Phase goal
- List of issues to address
- Tasks per issue
- Validation checklists
- Completion criteria

### Phase 1: Foundation (Weeks 1-2)
- Issue #3: Username Normalization
- Issue #4: Role Mapping Authority
- Issue #9: Configuration Management
- Issue #5: Test Infrastructure
**Deliverable:** Centralized core modules + test framework

### Phase 2: Core Architecture (Weeks 2-3)
- Issue #2: API Client Coupling & DI
- Issue #1: Database Schema Refactoring
**Deliverable:** Decoupled services + normalized database

### Phase 3: Polish & Scale (Weeks 3-4)
- Issue #7: Discord Timezone Bugs
- Issue #8: Performance Optimization
- Issue #11: Observability
**Deliverable:** Optimized, observable, production-ready system

### Phase 4: Integration & Testing (Week 4+)
- Full pipeline testing
- Regression testing
- Load testing
- Production rollout

---

## ✅ Pre-Implementation Checklist

Before starting, verify:

- [ ] **IMPLEMENTATION_PROGRESS.md** exists and is readable
- [ ] **IMPLEMENTATION_RULES.md** exists and has been reviewed
- [ ] **VS_CODE_WORKFLOW.md** exists and is understood
- [ ] **QUICK_REFERENCE.md** exists for quick lookup
- [ ] **check_implementation_status.py** runs without error
- [ ] **.vscode/settings.json** is updated with Python settings
- [ ] **.vscode/tasks.json** has 12+ automation tasks
- [ ] **.vscode/launch.json** has debug configurations
- [ ] **ClanStats.code-workspace** workspace file exists
- [ ] Git repository is initialized and clean (`git status` shows nothing)

**If ANY fail:** Fix it before proceeding. These are not optional.

---

## 🔄 Session Flow

### Start of Session
1. Read: IMPLEMENTATION_RULES.md (rules don't change, but refresh weekly)
2. Open: IMPLEMENTATION_PROGRESS.md
3. Find: Current task status (look for 🟠 IN PROGRESS or first ⬜)
4. Resume: Exactly where you left off

### During Session (Every 30 Minutes)
1. Update: IMPLEMENTATION_PROGRESS.md with current work
2. Check: `python check_implementation_status.py`
3. Verify: No breaking changes to existing code
4. Save: Work locally (don't commit yet)

### Task Completion
1. Finish: All code, tests, and validation for task
2. Update: IMPLEMENTATION_PROGRESS.md with evidence
3. Validate: Checklist items are 100% complete
4. Test: `pytest tests/ -v` passes
5. Commit: With message referencing task number

### End of Session
1. Verify: All work is committed
2. Check: `python check_implementation_status.py` passes
3. Update: IMPLEMENTATION_PROGRESS.md with next steps
4. Copy: Session Handoff Template for next session
5. End: Session ready for context reset

---

## 🚨 Critical Rules (Absolute Must-Follows)

**RULE #1:** IMPLEMENTATION_PROGRESS.md is THE source of truth
- All other decisions flow from it
- Must be updated every 30 minutes
- Cannot work on tasks not listed in it

**RULE #2:** Tests must pass before ANY commit
- `pytest tests/ -v` shows no failures
- No exceptions, no "I'll fix it later"
- All tests must pass or work does not commit

**RULE #3:** One task at a time
- Complete current task before starting next
- Complete = code + tests + validation + checklist
- No partial tasks

**RULE #4:** Validation checklist is mandatory
- Every checklist item must be verified
- Evidence (test output) must be in progress file
- "Looks good" is not sufficient

**RULE #5:** Clear commit messages
- Format: `Phase.Issue.Task: Name - Details`
- Must reference task from IMPLEMENTATION_PROGRESS.md
- Example: `Phase 1.3.1: Issue#3 Username Normalization - Created UsernameNormalizer class`

---

## 📊 Success Metrics

**You're succeeding when:**

| Metric | Target | Verification |
|--------|--------|--------------|
| Progress file updated | Every 30 min | Check modification time |
| All tests passing | 100% | Run `pytest tests/ -v` |
| Validation checklist | 100% complete | Check IMPLEMENTATION_PROGRESS.md |
| Commit frequency | 1 per task | Run `git log --oneline` |
| Clear status | Always known | 0 ambiguity in progress file |
| Pre-commit validation | Passes | Run `check_implementation_status.py` |

---

## 🎓 Documentation Map

```
RULES_SYSTEM_SETUP.md (this file)
├─ Authority Hierarchy
├─ How the system works
└─ Quick navigation guide

IMPLEMENTATION_PROGRESS.md
├─ Phase 1: Foundation
├─ Phase 2: Core Architecture
├─ Phase 3: Polish & Scale
├─ Phase 4: Integration
└─ Issues Encountered (for blocking issues)

IMPLEMENTATION_RULES.md
├─ 10 Core Rules
├─ Phase-Specific Rules
├─ Anti-Patterns to Avoid
└─ Enforcement Mechanisms

VS_CODE_WORKFLOW.md
├─ Daily startup
├─ During work
├─ Task execution
└─ Emergency procedures

QUICK_REFERENCE.md
├─ Commands
├─ Shortcuts
└─ Checklists
```

---

## 🔗 Integration Points

### Git Integration
- Every commit message references IMPLEMENTATION_PROGRESS.md task
- Commit history shows clear progression through phases
- Pre-commit hook validation (check_implementation_status.py)

### VS Code Integration
- Tasks (Cmd+Shift+P) prompt progress file review
- Settings configured for Python linting/testing
- Launch configs reference IMPLEMENTATION_PROGRESS.md

### Test Integration
- Tests are listed in IMPLEMENTATION_PROGRESS.md
- Test output is pasted into progress file as evidence
- Test coverage targets (80%+) are in rules

### Database Integration
- All schema changes tracked in IMPLEMENTATION_PROGRESS.md Phase 2
- Backups required before migrations
- Integrity tests validate migrations

---

## ❓ FAQ

**Q: What if I think a task should be different?**  
A: Update it in IMPLEMENTATION_PROGRESS.md, note the change in git commit message, continue work

**Q: Can I work on multiple tasks at once?**  
A: NO. One task at a time. Complete before moving on.

**Q: What if tests fail?**  
A: Fix the code or test. Re-run until passing. Then commit.

**Q: I forgot to update the progress file**  
A: Update it now. Include evidence from previous work.

**Q: How often should I commit?**  
A: After every completed task. Minimum: every 2-3 hours.

**Q: Context window is full, what do I do?**  
A: Save all work, commit changes, update progress file with handoff info, start new session

**Q: I'm stuck on a problem**  
A: Document in "Issues Encountered" section of progress file with full details

**Q: Is this overkill?**  
A: No. Complex projects need clear structure. This keeps you focused and prevents context loss.

---

## ✨ Final Notes

This system exists to:
✅ Keep you focused on one task at a time  
✅ Provide clear authority when decisions conflict  
✅ Enable context preservation across sessions  
✅ Prevent scope creep and off-plan work  
✅ Ensure quality through automated validation  
✅ Create an audit trail of progress  

**Remember:** The rules aren't restrictions. They're guardrails.  
They protect you from getting lost, from making bad commits, from losing progress.

---

**All systems ready. Let's implement.** 🚀

Last Updated: 2025-12-22  
Maintained By: Implementation Authority System
