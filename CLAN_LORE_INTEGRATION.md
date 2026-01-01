# Clan Lore Integration - Enhanced AI Insights

## Summary

Integrated the manually-improved `data/clan_lore.md` into the AI insights generation script. The lore now actively shapes how insights are created.

## What Changed

### 1. **Lore File Already Being Loaded**

- File: `data/clan_lore.md` (2,540 characters - concise but valuable)
- It was already being loaded in `scripts/mcp_enrich.py`
- Now properly leveraged in prompt instructions

### 2. **Enhanced Prompt Instructions**

**Added:**

- **The Golden Rule**: `Messages > Boss KC > XP` - emphasizing that chatters/yappers are more valuable than grinders
- **Duckling Detection**: Identifies new players to Tombs of Amascut for celebration moments
- **Clan Terminology Usage**: Instructions to use "Spoon", "Dry", "The Grind" appropriately
- **Nickname References**: Apply personas like "The Golden Boy" (docofmed)
- **Yapper vs Ghost Dynamic**: Contrast between communicative players and silent grinders
- **Clan Tone**: "Keep language chill and irreverent matching clan's 'banter, a lot' vibe"

### 3. **Simplified Leadership Context**

Removed redundant static leadership lists. Now references the lore's actual hierarchy:

```
- Owner: partymarty94 (dev, codes, hates agility)(highest rank)
- Deputy-owners: docofmed, jbwell, mtndck, maakif (2nd highest rank)
- Zenytes: jakestl314, psilocyn (3rd highest rank)
- Dragonstones: Sir Gowi, VanVolter II (3rd highest ran as well)
- Saviour: 4th highest rank
- All other ranks selected (5th highest rank)
- Prospector (new guys often) (6th highest rank)
```

## Benefits

✅ **Better Insights**: AI now generates content aligned with clan values
✅ **Smarter Tone**: Uses clan terminology and personality
✅ **Player-Aware**: Can spot Ducklings, highlight Yappers, celebrate The Grind
✅ **More Authentic**: Reflects actual clan culture, not generic stats
✅ **Token Efficient**: Removed duplicate leadership info (~200 tokens saved)

## How It Works

1. Script loads `clan_lore.md` into memory
2. Lore inserted as `**Clan Context:**` section in prompt
3. Mission statement references The Golden Rule, Ducklings, Yappers, etc.
4. AI generates 6 insights using both data + lore context
5. Output maintains clan personality and values

## Example Integration Points

**From Lore** → **Applied in Prompt**

- "Messages > Boss KC > XP" → "Look for Yappers (high messages)"
- "Ducklings (low ToA KC)" → "If anyone has low ToA KC, that's a celebration"
- "Spoon/Dry/The Grind" → "Use Clan Terminology in insights"
- "The Golden Boy" = docofmed → "Reference nicknames when applicable"
- "Banter, a lot" → "Keep language chill and irreverent"

## Files Updated

✅ `scripts/mcp_enrich.py`

- Enhanced mission statement with lore-based directives
- Simplified leadership context (removed ~200 tokens)
- Added Golden Rule emphasis
- Added Duckling detection instruction
- Added terminology usage guidance

## Test Results

✅ **All 145 tests passing** - No regressions

## Next: Testing with Actual Generation

Once quota resets, run to see lore-informed insights:

```bash
$env:LLM_PROVIDER = "2"
python scripts/mcp_enrich.py
```

Expected behavior: Insights now reference clan values, terminology, and dynamics from the lore.