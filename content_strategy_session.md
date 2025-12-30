# ClanStats Content Strategy: "The 12 Commandments"

**created**: 2025-12-30
**Goal**: Revamp AI insights to be social-first, banter-heavy, and visually distinct.

---

### I. Data Selection (Backend Logic)

**1. THE "ACTIVE ONLY" GATEKEEP**

* **Action**: Strictly filter the player list sent to the API.
* **Rule**: Include ONLY players with >0 XP **OR** >0 Boss Kills **OR** >0 Messages in the **last 14 days**.
* **Result**: Zero "Ghost" data sent to AI. Maximizes token efficiency for active members.

---

### II. The Prompt & Content Rules

**2. THE GOLDEN RULE (Yappers First)**

* **Instruction**: "Messages > Boss KC > XP. A chatter is the heart of the clan. Always highlight high message counts before high XP."

**3. LEADERSHIP BANTER (The 'Touches Grass' Index)**

* **Instruction**: "Compare Leaders (Marty/Doc) to the 'Average Joe'. If Marty has 40M Slayer XP (Top 1%), frame it as an outlier compared to the clan average. Banter is allowed (e.g., 'Only top 1%?')."

**4. NO "CHASING" NARRATIVES**

* **Instruction**: "Focus on **Individual Performance**. Do NOT use 'PlayerX is chasing PlayerY's record'. Celebrate the achievement on its own merit."

**5. THE "ANALYTICAL TREND" STRICT FORMAT (Banter Edition)**

* **Instruction**: "For the Weekly Trend, strictly compare the **Total Message Count of the last 7 Days** vs **The 7 Days Prior**."
  * *If Positive (>0%)*: "'This week there have been [X]% more messages compared to last week, gz gz'"
  * *If Negative (<0%)*: "'Activity dropped by [X]%... dying clan? Wake up scapers!'"

**6. THE ANOMALY HUNTER**

* **Instruction**: "Hunt for the 'Weirdos' among active players: The Wintertodt-Only hero, or the 1kc Boss Sampler."

**7. VISUAL VARIETY (Specific Matching)**

* **Instruction**: "Visuals must be specific: (A) Rank Icon, (B) Highest Skill Icon, or (C) Top Boss Icon. **Never** use a random generic asset."

**8. QUANTITY: THE "FULL DOZEN"**

* **Instruction**: "Generate exactly **10-12 Insights**. Ensure a mix of types (Leadership, Trends, Weird Stats, Spotlights)."

**9. QUIET GRINDERS (Numbers Only)**

* **Instruction**: "For silent high-performers, just show their massive stats. Do NOT label them 'Ghosts'. Let the numbers speak."

**10. DATA FIDELITY**

* **Instruction**: "Zero Hallucinations. If data is missing (e.g. unknown join date), skip the insight. Do not guess."

---

### III. Frontend Experience

**11. CARD DESIGN ("Big & Bold")**

* **Action**: CSS changes to make cards **Larger** to fill the screen better.
* **Action**: Avoid "Wall of Text" feeling; make them punchy.

**12. VISUAL DISTINCTION**

* **Action**: Distinct styling/borders based on Insight Type:
  * **Leadership**: Gold/Legendary styling.
  * **Trend**: Informational/Blue (or Red if "dying clan").
  * **Spoon/RNG**: Green/Sparkle.
  * **Roast/Banter**: Fire/Red.
