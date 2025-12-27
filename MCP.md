# MCP User Guide: Talking to Your Database

NOTE

This guide explains how to use the **Model Context Protocol (MCP)** to interact with your ClanStats database (

clan_data.db) using natural language. No SQL knowledge required!

## What is MCP?

MCP matches your natural language requests to specific tools defined in the system. Your agent has been equipped with a **Database Server** that allows it to:

* **Read** : Execute `SELECT` queries to find data.
* **Write** : Execute `INSERT/UPDATE/DELETE` queries to modify data.
* **Explore** : List tables and describe schemas to understand the data structure.

---

## How to "Talk" to Your Data

You can ask questions directly in the chat, and the agent will translate them into SQL.

### 1. Forensics & Investigations

Find specific patterns or "ghost" users.

**You Ask:**

> "Find users who have sent messages in the last 7 days but have 0 XP gain." "Who are the top 5 talkers who haven't bossed in a month?"

**Agent Does:**

* Joins `discord_messages` and `wom_snapshots`.
* Filters by

  timestamp and `total_xp`.
* Returns a list of suspects.

### 2. Fun Stats & Leaderboards

Generate custom leaderboards on the fly without writing code.

**You Ask:**

> "Who has the most Vorkath kills?" "Create a list of everyone with over 100 CoX kc compared to their entry mode kc."

**Agent Does:**

* Queries `boss_snapshots`.
* Groups by `boss_name = 'vorkath'`.
* Sorts by `kills DESC`.

### 3. Schema Exploration

Understand what data you have.

**You Ask:**

> "What data do we track for bosses?" "Show me the columns in the discord_messages table."

**Agent Does:**

* Calls `describe_table('boss_snapshots')`.
* Tells you about `rank`,

  kills, `boss_name`.

---

## Extending functionality (Advanced)

You can ask the agent to create new tables for events without touching the codebase.

**Example: Bingo Event** **You Ask:**

> "Create a new table called `bingo_2025` to track team points. It needs a team name, score, and members."

**Agent Does:**

<pre><div node="[object Object]" class="relative whitespace-pre-wrap word-break-all p-3 my-2 rounded-sm bg-list-hover-subtle"><div class="w-full h-full text-xs cursor-text"><div class="code-block"><div class="code-line" data-line-number="1" data-line-start="1" data-line-end="1"><div class="line-content"><span class="mtk6">CREATE</span><span class="mtk1"></span><span class="mtk6">TABLE</span><span class="mtk1"></span><span class="mtk16">bingo_2025</span><span class="mtk1"> (</span></div></div><div class="code-line" data-line-number="2" data-line-start="2" data-line-end="2"><div class="line-content"><span class="mtk1">    id </span><span class="mtk6">INTEGER</span><span class="mtk1"></span><span class="mtk6">PRIMARY KEY</span><span class="mtk1">,</span></div></div><div class="code-line" data-line-number="3" data-line-start="3" data-line-end="3"><div class="line-content"><span class="mtk1">    team_name </span><span class="mtk6">TEXT</span><span class="mtk1">,</span></div></div><div class="code-line" data-line-number="4" data-line-start="4" data-line-end="4"><div class="line-content"><span class="mtk1">    score </span><span class="mtk6">INTEGER</span><span class="mtk1"></span><span class="mtk6">DEFAULT</span><span class="mtk1"></span><span class="mtk7">0</span><span class="mtk1">,</span></div></div><div class="code-line" data-line-number="5" data-line-start="5" data-line-end="5"><div class="line-content"><span class="mtk1">    ...</span></div></div><div class="code-line" data-line-number="6" data-line-start="6" data-line-end="6"><div class="line-content"><span class="mtk1">);</span></div></div></div></div></div></pre>

**Verification:**

> "Verify the table exists." -> `list_tables()`

---

## Troubleshooting

If the agent says "Tool not found" or "Connection failed":

1. Ensure the MCP server is running (`docker mcp gateway run`).
2. Check that the

   ./.agent/tools.yaml file correctly points to `database-server`.

TIP

You don't need to specify "Use MCP". Just ask the question! The agent is smart enough to know when to look in the database.
