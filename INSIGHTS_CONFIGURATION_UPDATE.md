# Configuration Update: Reduced Insights from 13-15 to 6 Total

## Changes Made

### 1. **Updated Insight Generation Configuration**

**From:** 7 leadership + 6-8 supporting = 13-15 total insights  
**To:** 3 leadership + 3 supporting = 6 total insights

### 2. **Files Modified**

#### `scripts/mcp_enrich.py`

**Part 1 (Leadership Insights):**
- Changed: "Create exactly 7 insights" → "Create exactly 3 insights"
- Updated description: Focus on top leaders (Owner, Zenytes, Deputy Owners)
- Updated logging: "7 leadership insights" → "3 leadership insights"

**Part 2 (Supporting Players):**
- Changed: "Create 6-8 insights" → "Create exactly 3 insights"
- Updated description: Focus on supporting top-performing players
- Updated logging: "6-8 supporting player insights" → "3 supporting player insights"

**Key Parameters Unchanged:**
- ✅ Sleep duration: Still 25 seconds between Part 1 and Part 2
- ✅ Model provider: Still configurable via `LLM_PROVIDER` environment variable
- ✅ Token limits: Still 4096 max tokens per request
- ✅ Temperature: Still 1 (creative generation)

#### `SESSION_GEMINI_RATE_LIMITS.md`

**Payload Split Section:**
```markdown
1. **Part 1**: 3 leadership-focused insights
2. **Sleep**: 25 seconds (respecting quota reset window)
3. **Part 2**: 3 supporting player insights
4. **Combine**: Total 6 insights with diverse coverage
```

**Verification Output:**
```
Sending PART 1 request to gemini-2.5-pro API (3 leadership insights)...
Generated 3 insights (Part 1).
Sleeping 25s to avoid token rate limit (respecting free tier quota)...
Sending PART 2 request to gemini-2.5-pro API (3 supporting player insights)...
Generated 3 insights (Part 2).
Combined: 6 total insights.
```

#### `docs/GEMINI_RATE_LIMITS.md`

Updated code example to show 3 insights per part instead of 7/6-8.

### 3. **Benefits of This Change**

✅ **Reduced API token consumption** (fewer insights = fewer tokens)  
✅ **Faster generation** (3 insights instead of 13-15)  
✅ **Lower quota usage** (stays well within free tier limits)  
✅ **Simpler payloads** (easier to manage and test)  
✅ **More focused output** (quality over quantity)  
✅ **Still maintains diversity** (3 leadership + 3 supporting = good coverage)

### 4. **Test Results**

✅ **All 145 unit tests passing** - No regressions from changes

### 5. **Usage**

The configuration change is automatic. Running the script generates 6 insights instead of 13-15:

```bash
# Default (uses Groq)
python scripts/mcp_enrich.py

# With gemini-2.5-pro (once quota resets)
$env:LLM_PROVIDER = "2"
python scripts/mcp_enrich.py

# With gemini-2.5-flash (always available)
$env:LLM_PROVIDER = "1"
python scripts/mcp_enrich.py
```

Expected total runtime: ~30-35 seconds (including 25s sleep between parts)
