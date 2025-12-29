# Token Optimization Strategies for AI Insights Script

## Current Token Usage Analysis

**Current implementation:**
- Two API calls (Part 1 + Part 2) with identical base prompt
- Large prompt includes: clan lore, detailed player stats, extensive constraints, asset lists, leadership context, mission statement
- Estimated tokens per request: 2,500-3,500+ (before response)
- Total per run: ~5,000-7,000+ tokens consumed

## High-Impact Optimizations

### 1. **Consolidate Into Single Request (HIGHEST IMPACT)**

**Current:** 2 requests × ~3000 tokens each = ~6000 tokens  
**Optimized:** 1 request × ~3000 tokens = ~3000 tokens  
**Savings: 50%**

Instead of Part 1 (3 leadership) + 25s sleep + Part 2 (3 supporting):
- Request all 6 insights in one prompt with clear numbering
- Risk: Single quota hit, but 3000 tokens well within free tier quota
- Benefit: Instant response, no waiting, simpler code

```python
# Before: 2 requests with sleep
prompt = base_prompt + """Create 3 leadership insights"""
response1 = llm_client.generate(prompt)  # ~3000 tokens
time.sleep(25)
prompt = base_prompt + """Create 3 supporting insights"""  
response2 = llm_client.generate(prompt)  # ~3000 tokens

# After: 1 request
prompt = base_prompt + """Create exactly 6 insights: 3 leadership (lines 1-3), 3 supporting (lines 4-6)"""
response = llm_client.generate(prompt)  # ~3000 tokens
```

### 2. **Remove Clan Lore Content (HIGH IMPACT)**

**Current:** Entire `clan_lore.md` loaded and included  
**Impact:** ~500-1000+ tokens per request × 2 = ~1000-2000 tokens wasted  
**Savings: 15-25%**

**Solution:** Remove the lore content - it's not being used effectively

```python
# Before:
lore_content = ""
try:
    if os.path.exists(lore_path):
        with open(lore_path, "r", encoding="utf-8") as f:
            lore_content = f.read()  # Could be 2000+ tokens
except Exception:
    pass

prompt = f"""
**Clan Context:**
{lore_content}
"""

# After: Remove entirely, focus on player data instead
# Lore isn't critical for generating insights from actual player stats
```

### 3. **Simplify Prompt Constraints (MEDIUM IMPACT)**

**Current:** Extensive repeated constraints, multiple examples  
**Savings: 10-15%**

**Reduce from:**
```
**CRITICAL CONSTRAINTS:**
1. ONLY use facts from player data below - ZERO INVENTIONS OR HALLUCINATIONS
2. If data doesn't support a claim, SKIP THAT INSIGHT
3. Each insight must reference specific player(s) by name with exact numbers
4. Maximum 15 words per insight message
5. **MUST use DIFFERENT image for each insight - NO REPEATS EVER**

**Asset Selection Strategy - CRITICAL:**
- EACH insight MUST use a DIFFERENT image (never repeat an image)
- Skill stories → skill_*.png images
- Combat/boss stories → different boss_*.png images each time
- Rank/achievement stories → rank_*.png images
- Constantly rotate through the asset pool
- **Failing to diversify images is a critical failure**

[More constraints...]
```

**To:**
```
**CONSTRAINTS:**
1. Use ONLY provided player data - no inventions
2. Reference specific player names and exact numbers
3. Max 15 words per message
4. Use different image per insight
5. Format: {"type": "...", "title": "...", "message": "...", "image": "...", "icon": "..."}
```

### 4. **Use JSON Format for Player Data (MEDIUM IMPACT)**

**Current:** Narrative format (more tokens):
```
1. partymarty94: 463,868,162 XP, 25,178 boss kills
2. jakestl314: 304,525,690 XP, 6,316 boss kills
```

**Optimized:** Compact JSON (fewer tokens):
```json
[{"u":"partymarty94","x":463868162,"b":25178},{"u":"jakestl314","x":304525690,"b":6316}]
```

**Savings: 10-20%** (compact representation)

### 5. **Don't List All Assets (MEDIUM IMPACT)**

**Current:**
```python
skill_assets = [a for a in assets if a.startswith('skill_')]  # Hundreds of filenames
boss_assets = [a for a in assets if a.startswith('boss_')]    # Hundreds of filenames
rank_assets = [a for a in assets if a.startswith('rank_')]    # Hundreds of filenames

prompt += f"""
**Available Assets:**
Skills: {json.dumps(skill_assets)}  # Thousands of tokens for asset names
Bosses: {json.dumps(boss_assets)}
Ranks: {json.dumps(rank_assets)}
"""
```

**Optimized:**
```python
prompt += """
**Available Assets:**
Skills (skill_*.png), Bosses (boss_*.png), Ranks (rank_*.png)
Pick diverse images - varies available. Pick any random image names matching these patterns.
"""
```

**Savings: 20-30%** (removing hundreds of asset filenames)

### 6. **Reduce max_tokens (LOW IMPACT)**

**Current:** `max_tokens=4096` per request  
**Optimized:** `max_tokens=2048` or `max_tokens=1500`

For 6 insights in JSON format, 1500-2000 tokens is plenty.

**Savings: 5-10%** (reduces response token allocation)

### 7. **Remove Redundant Leadership Context**

**Current:** Repeats leadership info multiple times
```
**CLAN LEADERSHIP (Real Ranks):**
- Owner: partymarty94...
- Zenyte #1: jakestl314...
[repeats in various forms throughout]

**Leadership Context:**
- partymarty94 (Owner) leads by 52% over first zenyte
[more repeats]
```

**Optimized:** Include once, reference in instructions

## Recommended Implementation Plan

### Phase 1: Quick Wins (30-50% token reduction)
1. ✅ Consolidate to single request (save 50%)
2. ✅ Remove clan lore loading (save 15-25%)
3. ✅ Simplify constraints (save 10-15%)
4. ✅ Don't list all assets (save 20-30%)

**Combined: ~40-60% total reduction**

### Phase 2: Refinement (5-10% additional)
1. Reduce max_tokens to 2048
2. Use compact JSON for player data
3. Remove redundant leadership context

**Combined: Additional 10-15%**

### Phase 3: Advanced (Optional)
1. Consider using cheaper model (gemini-2.5-flash-lite or groq)
2. Implement request caching/batching
3. Use compressed prompts for repeated runs

## Specific Code Changes

### Option A: Minimal Changes (Keep Split Requests)
```python
# Remove lore entirely
# lore_content = ...  # DELETE THIS SECTION

# Simplify prompt
prompt = f"""
You are the Clan Chronicler for The 0ld G4ng (OSRS clan).
Use ONLY provided data. No inventions. Reference player names + exact numbers.
Max 15 words per message. Use different image for each insight.

Player Data:
{player_detail}

Available Assets: skill_*.png, boss_*.png, rank_*.png

Output JSON array: {{"type":"...", "title":"...", "message":"...", "image":"...", "icon":"..."}}

{leadership_context}

Create exactly 3 leadership insights about top leaders.
"""
```

### Option B: Maximum Savings (Single Request)
```python
prompt = f"""
You are the Clan Chronicler for The 0ld G4ng OSRS clan.
Create 6 JSON insights from player data: 3 leadership (top players), 3 supporting (strong contributors).
ONLY use facts from data. Reference player names + numbers. Max 15 words each. Different image per insight.

Players: {compact_json_player_data}

Leadership (by XP): {top_3_leadership}
Supporting: {next_3_players}

Assets: skill_*.png, boss_*.png, rank_*.png

Output: JSON array of 6 objects
"""

response = llm_client.generate(prompt, max_tokens=2048, temperature=1)
```

## Token Usage Comparison

| Strategy | Tokens/Run | Savings | Time | Benefit |
|----------|-----------|---------|------|---------|
| **Current** | ~6000 | — | 30s | Stable |
| **Phase 1** | ~2400 | 60% | 5s | Major savings |
| **Phase 2** | ~1800 | 70% | 5s | Max efficiency |
| **Single Req** | ~3000 | 50% | 5s | Simple + fast |

## Recommended Approach

**Best balance of savings + simplicity:**

1. Consolidate to single request (save 50%)
2. Remove clan lore (save 20%)
3. Simplify constraints (save 15%)
4. Remove asset listing (save 25%)
5. Reduce max_tokens to 2048 (save 10%)

**Total: ~60-70% token reduction** from ~6000 to ~2000-2400 tokens per run

**No functionality loss** - same 6 insights, much cheaper
