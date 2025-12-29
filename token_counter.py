import os
import json
import random
from dotenv import load_dotenv

# Load environment
load_dotenv()
os.chdir("d:\\Clan_activity_report")

# Load sample data
lore_path = "data/clan_lore.md"
with open(lore_path, "r") as f:
    lore_content = f.read()

# Load sample assets
assets_path = "data/assets.json"
with open(assets_path, "r") as f:
    all_assets = json.load(f)

# Mock player data (realistic)
players = [
    {"username": "partymarty94", "total_xp": 5234000, "total_boss_kills": 2341},
    {"username": "docofmed", "total_xp": 4521000, "total_boss_kills": 1923},
    {"username": "jbwell", "total_xp": 3892000, "total_boss_kills": 1654},
    {"username": "mtndck", "total_xp": 3456000, "total_boss_kills": 1321},
    {"username": "jakestl314", "total_xp": 2987000, "total_boss_kills": 987},
    {"username": "psilocyn", "total_xp": 2654000, "total_boss_kills": 854},
    {"username": "Netfllxnchll", "total_xp": 2341000, "total_boss_kills": 762},
    {"username": "TheForgeGod", "total_xp": 2123000, "total_boss_kills": 645},
    {"username": "Player9", "total_xp": 1987000, "total_boss_kills": 534},
    {"username": "Player10", "total_xp": 1654000, "total_boss_kills": 421},
    {"username": "Player11", "total_xp": 1523000, "total_boss_kills": 387},
    {"username": "Player12", "total_xp": 1234000, "total_boss_kills": 298},
    {"username": "Player13", "total_xp": 987000, "total_boss_kills": 234},
]

player_detail = "\n".join([
    f"  {i+1}. {p.get('username', 'Unknown')}: {p.get('total_xp', 0):,} XP, {p.get('total_boss_kills', 0):,} boss kills"
    for i, p in enumerate(players)
])

# Sample assets - NOW USE ALL ASSETS (no sampling)
bosses_all = all_assets.get("bosses", [])  # All 79 bosses
skills_all = all_assets.get("skills", [])  # All 24 skills
all_ranks = []
for rank_category in all_assets.get("ranks", {}).values():
    if isinstance(rank_category, list):
        all_ranks.extend(rank_category)
ranks_all = all_ranks  # All 270 ranks

# Build the full prompt
prompt = f"""
You are the Clan Chronicler for an Old School RuneScape clan (The 0ld G4ng).
Your ONLY source of truth is the player data provided. DO NOT INVENT ANY FACTS.

**Clan Context:**
{lore_content}

**CRITICAL CONSTRAINTS:**
1. ONLY use facts from player data below - ZERO INVENTIONS OR HALLUCINATIONS
2. If data doesn't support a claim, SKIP THAT INSIGHT
3. Each insight must reference specific player(s) by name with exact numbers
4. Maximum 15 words per insight message
5. **MUST use DIFFERENT image for each insight - NO REPEATS EVER**

**PLAYER DATA (Your ONLY Source of Truth):**
{player_detail}

**Available Assets** (pick diverse images, rotate through types):
Skills (for XP/training/efficiency stories): {', '.join(skills_all)}
Bosses (for combat achievements): {', '.join(bosses_all)}
Clan Ranks (for progression/role stories): {', '.join(ranks_all)}
Ranks (for milestone/achievement stories): rank_*.png files

**Asset Selection Strategy - CRITICAL:**
- EACH insight MUST use a DIFFERENT image (never repeat an image)
- Skill stories -> skill_*.png images
- Combat/boss stories -> different boss_*.png images each time
- Rank/achievement stories -> rank_*.png images
- Constantly rotate through the asset pool
- **Failing to diversify images is a critical failure**

**KEY INSIGHT: Apply The Golden Rule**
Messages > Boss KC > XP. A chatter is worth more than a grinder. Look for Yappers (high messages).

**Top Leaders by Rank (from Lore):**
- Owner: partymarty94 (dev, codes, hates agility)
- Deputy-owners: docofmed (The Golden Boy - high XP/KC/Messages), jbwell, mtndck
- Zenytes: jakestl314, psilocyn (both moderators, equal in hierarchy)

**Your Mission (Apply Clan Lore):**
1. Apply the Golden Rule: **Messages > Boss KC > XP** - Chatters/Yappers are THE heart of the clan
2. Spot Ducklings: If anyone has low ToA KC or just started ToA, that's a celebration moment
3. Use Clan Terminology: "Spoon" (blessed by RNG), "Dry" (testing faith), "The Grind" (meditative respect)
4. Reference Nicknames & Personas from lore when applicable (e.g., "The Golden Boy" = docofmed)
5. Highlight the contrast: Yappers vs Ghosts (high messages vs silent grinders)
6. Create 3 leadership insights: Focus on tier positioning, dominance, and clan importance
7. Create 3 supporting insights: Rising stars, Ducklings, or specialized achievements
8. Keep language chill and irreverent matching clan's "banter, a lot" vibe

**Output Rules:**
- Return ONLY valid JSON array with no markdown blocks
- Each object has: type, title, message, image, icon fields
- Types: trend, milestone, fun, battle, outlier
- **EVERY IMAGE MUST BE DIFFERENT - This is mandatory**
- **ONLY factual claims using real player names and numbers from data above**
- **MESSAGE FORMAT VARIETY** (do NOT use same template for all):
  * Comparative: "PlayerA leads with X vs PlayerB's Y"
  * Narrative: "From humble starts, PlayerX now dominates with..."
  * Question format: "Who holds the throne? PlayerX with..."
  * Challenge: "Can anyone match PlayerX's X achievement?"
  * Superlative: "The fastest grinder, highest killer, strongest force..."
  * Stat-driven: "Numbers tell the story: PlayerX stands at..."

Create exactly 6 insights (3 leadership, 3 supporting players).
Return ONLY a valid JSON array with 6 objects.
"""

# Count characters and estimate tokens
char_count = len(prompt)
print(f"📊 UNIFIED REQUEST (Single API Call)")
print(f"━" * 60)
print(f"Character count: {char_count:,}")
print(f"Word count: {len(prompt.split()):,}")
print()
print(f"Token Estimate (Gemini tokenization ~3.5 chars/token):")
print(f"  {char_count / 3.5:.0f} tokens (conservative)")
print()

# Current split approach
part1_suffix = "\n\nCreate exactly 3 insights focusing on top leaders (Owner, Zenytes, or Deputy Owners).\nReturn ONLY a valid JSON array with 3 objects."
part2_suffix = "\n\nCreate exactly 3 insights focusing on supporting top-performing players.\nUse COMPLETELY DIFFERENT images from Part 1.\nReturn ONLY a valid JSON array with 3 objects."

prompt_part1 = prompt + part1_suffix
prompt_part2 = prompt + part2_suffix

print(f"CURRENT APPROACH (Split Payload - 2 API Calls)")
print(f"━" * 60)
print(f"Part 1 chars: {len(prompt_part1):,}")
print(f"Part 1 tokens: ~{len(prompt_part1) / 3.5:.0f} tokens")
print()
print(f"Part 2 chars: {len(prompt_part2):,}")
print(f"Part 2 tokens: ~{len(prompt_part2) / 3.5:.0f} tokens")
print()
print(f"Total (Part 1 + Part 2): ~{(len(prompt_part1) + len(prompt_part2)) / 3.5:.0f} tokens")
print()

# Calculate savings
unified_tokens = char_count / 3.5
split_tokens = (len(prompt_part1) + len(prompt_part2)) / 3.5
savings = split_tokens - unified_tokens
savings_pct = (savings / split_tokens) * 100

print(f"📈 COMPARISON")
print(f"━" * 60)
print(f"Unified request (1 call):  ~{unified_tokens:.0f} tokens")
print(f"Split request (2 calls):   ~{split_tokens:.0f} tokens")
print(f"Overhead for split:        +{savings:.0f} tokens ({savings_pct:.1f}% duplication)")
print()
print(f"✅ Unified is more token-efficient by {savings_pct:.0f}%")
print(f"   But split respects 2 RPM rate limit (25s sleep required)")
