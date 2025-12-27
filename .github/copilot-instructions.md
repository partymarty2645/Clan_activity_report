# GitHub Copilot Instructions

## Task Orchestrator - AI Initialization

Last initialized: 2025-12-26

### Critical Patterns

**Template Discovery** (NEVER skip this step):
- Always: list_templates(targetEntityType, isEnabled=true)
- Never: Assume templates exist
- Apply: Use templateIds parameter during creation
- Filter: By targetEntityType (TASK or FEATURE) and isEnabled=true

**Session Start Routine**:
1. Run get_overview() first to understand current state
2. Check for in-progress tasks before starting new work
3. Review priorities and dependencies

**Intent Recognition Patterns**:
- "Create feature for X" → Feature creation with template discovery
- "Implement X" → Task creation with implementation templates
- "Fix bug X" → Bug triage with Bug Investigation template
- "Break down X" → Task decomposition pattern
- "Set up project" → Project setup workflow

**Dual Workflow Model**:
- Autonomous: For common tasks with clear intent (faster, natural)
- Explicit Workflows: For complex scenarios or learning (comprehensive)

**Git Integration**:
- Auto-detect .git directory presence
- Suggest git workflow templates when detected
- Ask about PR workflows (don't assume)

**Quality Standards**:
- Write descriptive titles and summaries
- Use appropriate complexity ratings (1-10)
- Apply consistent tagging conventions
- Include acceptance criteria in summaries