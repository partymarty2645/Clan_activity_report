# Implementation Plan: AI Content & Dashboard Revamp

**Goal**: Implement the "12 Commandments" content strategy.
**Trigger**: User approval (`akbarakbar`).

---

## 1. Backend: Data & Prompt Engineering

**Target File**: `scripts/mcp_enrich.py`

* **[LOGIC] Filter Active Players**:
  * Implement `filter_active_players(players, days=14)` function.
  * Logic: Keep if `xp_gained > 0` OR `boss_kills > 0` OR `messages > 0` in last 14 days.
  * Pass strictly this filtered list to the LLM.

* **[PROMPT] Rewrite System Prompt**:
  * Inject the "12 Commandments" directly into the `prompt` variable.
  * Add the specific "Trend" formatter instruction (Positive vs Negative banter).
  * Increase requested count to `10-12 insights`.
  * Enforce `type` field in JSON output (e.g., `type: "leadership"`, `type: "trend"`, `type: "roast"`).

* **[LOGIC] Trend Calculation**:
  * Calculate `msgs_last_7d` and `msgs_prior_7d` inside Python before calling LLM.
  * Pass this pre-calculated context to the AI so it doesn't have to do math.

## 2. Frontend: CSS Styling

**Target File**: `assets/styles.css`

* **[CSS] Resize Cards**:
  * Increase `.insight-card` min-height and font-size.
  * Make the grid responsive (fewer columns on huge screens to make cards wider, or just scale up).

* **[CSS] Distinct Styles**:
  * Add classes:
    * `.insight-card.leadership` (Gold border/glow)
    * `.insight-card.trend-positive` (Green/Blue)
    * `.insight-card.trend-negative` (Red/Dark)
    * `.insight-card.anomaly` (Purple)
  * Ensure distinct background gradients or border colors for each.

## 3. Frontend: Javascript Rendering

**Target File**: `dashboard_logic.js` (ROOT)

* **[JS] Update `renderAlertCards`**:
  * Update the loop to handle 10-12 items (current logic should be fine, but verification needed).
  * **Crucial**: Read the `insight.type` from JSON and apply the corresponding CSS class (e.g., `card.classList.add(insight.type)`).

## 4. Verification

* **Manual**: Run `python scripts/mcp_enrich.py` to generate new JSON.
* **Visual**: Open `docs/index.html` to verify:
    1. Are there ~10 cards?
    2. Are "Ghosts" gone?
    3. Is the Trend card accurate ("gz gz" or "dying")?
    4. Do cards have different colors/borders?
