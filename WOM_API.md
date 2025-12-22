# Wise Old Man (WOM) API Rules & Best Practices

## 1. Overview & Authentication

* **Base URL:** `https://api.wiseoldman.net/v2`
* **Documentation:** [docs.wiseoldman.net](https://docs.wiseoldman.net)
* **Authentication:**
  * **Method:** Header `x-api-key: <YOUR_API_KEY>`
  * **User-Agent:** **MANDATORY**. You must identify your client (e.g., `User-Agent: MyClanBot/1.0 discord_user`). Failure to do so may result in an IP ban.

## 2. Rate Limits

WOM enforces strict rate limits to protect their free service.

### A. Limits

| Type | Limit | Scope |
| :--- | :--- | :--- |
| **Standard (No Key)** | 20 requests / 60 seconds | Per IP |
| **Authenticated** | 100 requests / 60 seconds | Per IP |

### B. "Update" Limits (Important)

Updating a player (scanning their hiscores) is expensive.

* **Individual Player:** Limited to 1 update per 60 seconds per player (across all users).
* **Group Update:** Avoid triggering this too often. Best practice is **every 6-24 hours**.

### C. Best Practices

1. **Cache Data:** Do not fetch the same data twice.
2. **Linear Backoff:** IF you hit a 429, wait `Reset-Time + 1s` before retrying.
3. **Concurrency:** Limit concurrent requests (e.g., `aiohttp.Semaphore(5)`) to avoid spiking the server.

## 3. Key Endpoints for ClanStats

### A. Group Members (`GET /groups/{id}`)

* **Purpose:** Fetches the current member list.
* **Return Structure:**

    ```json
    {
      "id": 123,
      "name": "My Clan",
      "memberships": [
        {
          "player": { "username": "Player1", "id": 999 },
          "role": "member"
        }
      ]
    }
    ```

### B. Player Snapshots (`GET /players/{username}/snapshots`)

* **Purpose:** Fetches historical data points (XP, Kills, Ranks).
* **Query Params:** `?period=day` or specific dates.
* **Return Structure:** Array of Snapshot objects.
  * `data.skills`: (Attack, Strength, etc.) -> `{ metric, experience, rank, level }`
  * `data.bosses`: (Zulrah, Nex, etc.) -> `{ metric, kills, rank }`
  * `data.activities`: (Clues, LMS, etc.) -> `{ metric, score, rank }`

## 4. Error Handling Guide

### A. The "502 Bad Gateway" (Common)

* **Meaning:** WOM Server is down, restarting, or under eager load (common during game updates).
* **Handling:** **DO NOT PANIC**. This is external.
  * **Wait:** Retry in 5s, then 10s, then 30s.
  * **Abort:** If it fails 5 times, abort the harvest for that hour.

### B. Other Codes

* **400 Bad Request:** User likely changed name or does not exist on Hiscores.
* **402 Payment Required:** Restricted feature (Patreon-only).
* **403 Forbidden:** Invalid API Key. Check `.env`.
* **429 Too Many Requests:** You are going too fast. **SLEEP**.
* **500 Internal Server Error:** Bug on WOM side. treat same as 502.
