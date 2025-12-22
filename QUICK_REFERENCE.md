# ClanStats Implementation Quick Reference

## 🚀 Daily Startup
```bash
# 1. Open the workspace
code ClanStats.code-workspace

# 2. Read the rules (takes 5 min)
# Open: IMPLEMENTATION_RULES.md

# 3. Check progress
# Open: IMPLEMENTATION_PROGRESS.md

# 4. Find current task and start coding
```

## 💻 During Work Session

### Check Status Anytime
```bash
python check_implementation_status.py
```

### Run Tests (Required before commit)
```bash
pytest tests/ -v
```

### Check What Changed
```bash
git status
git diff
```

### Update Progress File
Open IMPLEMENTATION_PROGRESS.md and:
1. Find your current task
2. Change ⬜ to 🟠 IN PROGRESS
3. Add validation evidence
4. Change to ✅ when done

## 🧪 Test Commands

### All Tests
```bash
pytest tests/ -v
```

### Specific Test File
```bash
pytest tests/test_usernames.py -v
```

### With Coverage
```bash
pytest tests/ --cov=core,services,scripts --cov-report=html
```

### Quick Check
```bash
python check_implementation_status.py
```

## 💾 Git Commands

### Check status
```bash
git status
```

### Stage changes
```bash
git add .
```

### Commit with message
```bash
git commit -m "Phase.Issue.Task: Name - Details"

# Example:
git commit -m "Phase 1.3.1: Issue#3 Username Normalization - Added UsernameNormalizer class"
```

### View history
```bash
git log --oneline -10
```

## 🛠️ Important Commands

### Database Backup (REQUIRED before schema changes)
```bash
python scripts/backup_db.py
```

### Import test
```bash
python -c "import core.usernames; print('OK')"
```

### Full validation
```bash
python check_implementation_status.py && pytest tests/ -v
```

## 📋 Checklist Before Commit

```
☐ IMPLEMENTATION_PROGRESS.md updated (task marked ✅)
☐ Validation checklist items all verified
☐ Tests pass: pytest tests/ -v
☐ No import errors: python -c "import core..."
☐ Git clean: git status (shows nothing)
☐ Database backup created (if applicable)
☐ Commit message references task number
☐ check_implementation_status.py passes
```

If ANY fail, DO NOT COMMIT. Fix first.

## 🚨 Emergency Help

### Tests failing?
1. Read the error message carefully
2. Fix the code or test
3. Run tests again
4. Make sure they pass
5. Then commit

### Git confused?
```bash
# See what changed
git diff

# Undo changes to a file
git checkout <filename>

# See last few commits
git log --oneline -5
```

### Need to update progress?
```bash
# Just open the file and edit it
code IMPLEMENTATION_PROGRESS.md
```

## 📖 Important Files

- **IMPLEMENTATION_PROGRESS.md** - What to do next
- **IMPLEMENTATION_RULES.md** - Rules to follow
- **VS_CODE_WORKFLOW.md** - Detailed workflow guide
- **check_implementation_status.py** - Status validator

Open any with:
```bash
code <filename>
```

## 🎯 Remember

**RULE #1:** Follow IMPLEMENTATION_PROGRESS.md exactly
**RULE #2:** All tests must pass before commit
**RULE #3:** Update progress file every 30 minutes
**RULE #4:** One task at a time (complete before moving on)
**RULE #5:** Clear commit messages with task references

## ⏰ Session Management

### Ending Session?
1. Run: `python check_implementation_status.py`
2. Commit any outstanding work
3. Update IMPLEMENTATION_PROGRESS.md with current status
4. Note any blockers or next steps
5. Copy Session Handoff Template to progress file

### Starting New Session?
1. Read: IMPLEMENTATION_PROGRESS.md
2. Find: Current task status
3. Resume: From exact point you left off
4. Continue: With clear understanding of context

---

**Questions?** → Check IMPLEMENTATION_RULES.md → Check IMPLEMENTATION_PROGRESS.md → Ask in "Issues Encountered" section

**Need workflow help?** → See VS_CODE_WORKFLOW.md

**Ready to commit?** → Run: `python check_implementation_status.py`
