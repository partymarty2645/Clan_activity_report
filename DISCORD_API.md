# Discord API Rules & Best Practices

## 1. Overview & Authentication

* **Base URL:** `https://discord.com/api/v10`
* **Authentication:** Bot Token (Header: `Authorization: Bot <TOKEN>`)
* **Intents:**
  * **Required for Harvest:** `MESSAGE_CONTENT` (to read message text), `GUILD_MEMBERS` (to map IDs to names).
  * **Setup:** These must be explicitly enabled in the [Discord Developer Portal](https://discord.com/developers/applications) under the "Bot" tab.

## 2. Rate Limits

Discord uses a complex, tiered rate limit system.

### A. Global Rate Limit

* **Limit:** 50 requests per second.
* **Scope:** Per Bot.
* **Action if Exceeded:** 429 Too Many Requests (Global). The library (`discord.py`) handles this automatically, but extreme violations will result in a temporary IP ban by Cloudflare.

### B. Route-Specific Limits (Per Endpoint)

Limits vary by endpoint. A "bucket" system tracks these.

* **Channel Messages (`GET /channels/{id}/messages`):**
  * **Limit:** ~50 requests per second (varies, but high capacity).
  * **Batch Size:** Max **100 messages** per request.
  * **Reset:** Check `X-RateLimit-Reset` header.
* **Message Create (`POST /channels/{id}/messages`):**
  * **Limit:** 5 requests per 4 seconds per channel.

### C. Gateway Limits (Real-time connection)

* **Identify (Login):** 1 request per 5 seconds. (Start limit: 1000 per day for small bots).
* **Presence Update:** 5 updates per 60 seconds.
* **Event Emission:** 120 events per 60 seconds (outbound).

### D. Invalid Request Limit (The "Cloudflare Ban" Rule)

* **Limit:** 10,000 invalid requests (401, 403, 404) per 10 minutes.
* **Consequence:** Temporary IP ban.
* **Fix:** Ensure logic halts immediately upon receiving distinct 401/403 errors (implemented in `harvest_sqlite.py`).

## 3. Best Practices: Single Channel Architecture

For bots operating in a "Single Channel" mode (like ClanStats):

### A. Permission Scoping

Instead of giving the bot `Administrator`:

1. **Disable** the bot's permission to View Channels by default (`@everyone`).
2. **Enable** "View Channel" and "Read Message History" **ONLY** for the target channel (`#osrs-clan-chat`).
3. **Benefit:** This prevents the bot from processing events from irrelevant channels, saving gateway bandwidth and processing power.

### B. Efficient Fetching Strategy

When refilling database history:

1. **Use `before` and `after` IDs:** Never fetch by index. Always ask for 100 messages *before* the oldest ID you have (for history) or *after* the newest (for sync).
2. **Filter Empty/System Messages:** Discard messages with no content or system types (e.g., "User joined the server") immediately to save DB space.
    * *Implemented in `services/discord.py`: Filters `type=DEFAULT` or `REPLY` only.*

### C. Error Handling

* **401 Unauthorized:** Token is invalid. **STOP** immediately. Do not retry.
* **403 Forbidden:** Bot lacks access to the specific channel. Check Channel Overrides.
* **429 Too Many Requests:** Respect the `Retry-After` header. `discord.py` does this natively, but ensure your custom scripts wait if they make raw requests.
* **50x Server Error:** Retry with exponential backoff.

## 4. Specific Configuration for ClanStats

* **Batch Size:** 100 (Max allowed).
* **Safety Delay:** 0.75s between chunks (Conservative to stay well under global limits).
* **Data Retention:** Store only `id`, `author_id`, `content`, `timestamp`.
