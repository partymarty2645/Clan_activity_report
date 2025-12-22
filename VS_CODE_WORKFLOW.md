# VS Code Implementation Workflow Guide

**Quick Reference for Daily Work**

---

## 🚀 Start of Session Checklist

### Step 1: Open Workspace
```bash
code ClanStats.code-workspace
```

### Step 2: Review Rules (Cmd+Shift+P)
```
Run Task: ⚖️ Review IMPLEMENTATION_RULES.md
```
*(Takes 5-10 minutes. Non-negotiable.)*

### Step 3: Check Progress (Cmd+Shift+P)
```
Run Task: 📋 Review IMPLEMENTATION_PROGRESS.md
```
*(Identifies current task. Find where you left off.)*

### Step 4: Identify Next Task
Look for first ⬜ NOT STARTED in current phase (found in progress file)

---

## 💻 During Coding Session

### Every 30 Minutes
- [ ] Update IMPLEMENTATION_PROGRESS.md with current work
- [ ] Check `git status` to see uncommitted changes
- [ ] Verify no breaking changes to existing code

### Every Task Completion
1. **Update Progress File**
   ```
   - [x] **1.3.1 Create `core/usernames.py`**
   ```

2. **Run Tests**
   ```
   Cmd+Shift+P → "Run Task: 🧪 Run All Tests"
   ```

3. **Verify Validation Checklist**
   - Copy/paste test output into progress file
   - Mark all checklist items as done

4. **Commit Changes**
   ```bash
   git add .
   git commit -m "Phase.Issue.Task: Name - Details"
   ```

---

## 🧪 Testing Commands (Quick Access)

All available via `Cmd+Shift+P → Run Task:`

| Task | Purpose | Must Pass? |
|------|---------|-----------|
| `🧪 Run All Tests` | Complete test suite | ✅ REQUIRED |
| `✅ Phase 1: Run All Tests` | Phase-specific tests | ✅ REQUIRED |
| `📊 Test Coverage Report` | Coverage analysis (80%+ target) | ✅ REQUIRED |
| `🔐 Pre-Commit Validation` | Final checks before commit | ✅ REQUIRED |

**RULE:** Cannot commit until these pass:
```
✅ All tests pass
✅ No import errors
✅ No breaking changes
✅ Coverage >80% (for new code)
```

---

## 📊 Status Tracking Commands

### Check Uncommitted Work
```
Cmd+Shift+P → "Run Task: 💾 Git Status Check"
```

### View Commit History
```
Cmd+Shift+P → "Run Task: 📚 View Log"
```

### Database Backup (⚠️ Critical)
```
Cmd+Shift+P → "Run Task: 🛠️ Database Backup"
```
**RULE:** Before ANY database schema change, run this first.

---

## 🔄 End of Session Checklist

### Before Closing Editor
1. [ ] Run `🧪 Run All Tests` - all pass
2. [ ] Update IMPLEMENTATION_PROGRESS.md
3. [ ] Check `💾 Git Status Check` - clean (nothing uncommitted)
4. [ ] Commit all changes with clear message
5. [ ] Update Session Handoff Template in progress file

### Before Ending Chat Session
1. [ ] Paste current task status
2. [ ] Paste blockers/issues
3. [ ] Paste next 2-3 tasks to resume
4. [ ] Document anything unusual that happened

---

## 🎯 Task Execution Template

### When Starting a Task

**1. Mark In Progress**
```markdown
- [x] **1.3.1 Create `core/usernames.py`**
  - Status: 🟠 IN PROGRESS
```

**2. Open Relevant Files**
- [ ] Task description in IMPLEMENTATION_PROGRESS.md (already open)
- [ ] Related existing code files (for reference)
- [ ] New file you're creating (create in VS Code)

**3. Code Implementation**
- Write code following existing patterns
- Run tests after each major function
- Commit frequently (every function or every 30 minutes)

**4. Write Tests**
- Create test file
- Write test cases from specification
- Ensure 100% coverage of new functions

**5. Update Progress File**
```markdown
- [x] **1.3.1 Create `core/usernames.py`**
  - File: `core/usernames.py`
  - Status: ✅ DONE

#### Evidence
- Created core/usernames.py (165 lines)
- Created tests/test_usernames.py (94 lines)
- Test Results: 6/6 PASSING
- Validation: All checklist items verified ✅
```

**6. Commit**
```bash
git add core/usernames.py tests/test_usernames.py
git commit -m "Phase 1.3.1: Issue#3 Username Normalization - Created UsernameNormalizer class"
```

---

## 🚨 Emergency Commands

### "Tests are failing!"
1. Run the failing test individually (copy test name from output)
2. Read error message carefully
3. Fix code or test as appropriate
4. Re-run tests
5. Do NOT commit until passing

### "I broke something!"
1. Check what changed: `git diff`
2. Either revert: `git checkout <file>` or fix code
3. Re-run all tests
4. Then commit

### "Context window getting full!"
1. Commit ALL changes immediately
2. Update IMPLEMENTATION_PROGRESS.md with current status
3. Copy Session Handoff Template section to progress file
4. Start new chat session with context from progress file

### "I'm stuck on a problem!"
1. Document in IMPLEMENTATION_PROGRESS.md "Issues Encountered" section
2. Include: What you tried, error message, expected result
3. Don't guess - analyze the problem
4. Commit what you have so far

---

## 📈 Visual Status Indicators

### Task Status Icons
- ⬜ **NOT STARTED** - Haven't begun
- 🟠 **IN PROGRESS** - Currently working on it
- ✅ **COMPLETE** - Done and validated
- 🔴 **BLOCKED** - Waiting on something

### File Status in Git
- `M` = Modified (yellow)
- `A` = Added (green)
- `D` = Deleted (red)
- `?` = Untracked (purple)

**RULE:** Before committing, all modified files should be intentional.

---

## 🔗 Key Files at a Glance

| File | Purpose | Access |
|------|---------|--------|
| `IMPLEMENTATION_PROGRESS.md` | Source of truth | Cmd+P → type filename |
| `IMPLEMENTATION_RULES.md` | Rules to follow | Cmd+P → type filename |
| `core/usernames.py` | Phase 1 Task | Will create |
| `core/roles.py` | Phase 1 Task | Will create |
| `tests/conftest.py` | Test infrastructure | Will create |
| `.vscode/tasks.json` | Automation commands | Already set up |
| `.vscode/settings.json` | VS Code config | Already set up |
| `.vscode/launch.json` | Debug config | Already set up |

---

## 💡 Pro Tips

### 1. Keep Terminal Open
Have VS Code terminal open to see test output and git status real-time

### 2. Use Tasks Bar
Favorite frequently-used tasks (star icon) for quick access

### 3. Split Editor
Open IMPLEMENTATION_PROGRESS.md on left, code on right for reference

### 4. Search with Cmd+Shift+F
Find all usages of old function names when refactoring

### 5. Python REPL
Open Python terminal (`Ctrl+` `) to test small code snippets quickly

### 6. Git Blame
Hover over line to see when it was committed (useful for understanding context)

---

## 🎓 Learning Resources (Embedded in Workspace)

- **IMPLEMENTATION_PROGRESS.md** - Detailed task breakdown
- **IMPLEMENTATION_RULES.md** - Complete rule set
- **VSCODE_AUDIT.md** - Original audit findings
- **implementingplan.MD** - Strategic overview
- **README.md** - Project overview

---

## ✨ Success = Following This Exactly

✅ You're doing great when:
- IMPLEMENTATION_PROGRESS.md updates within every 30 minutes
- All tests pass before any commit
- Commit messages reference task numbers
- No uncommitted work at end of session
- New files follow existing code patterns
- Validation checklists are 100% complete

❌ You're off track when:
- Can't find current task in progress file
- Tests are failing but you're committing anyway
- Changes not mentioned in progress file
- Working on multiple tasks simultaneously
- More than 2 hours since last update to progress file

---

**Remember:** This file + IMPLEMENTATION_PROGRESS.md + IMPLEMENTATION_RULES.md = your complete playbook.

Every work session should feel like executing a predetermined plan, not inventing as you go.
