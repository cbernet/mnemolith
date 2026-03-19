# Claude Integration

Mnemolith gives Claude access to your personal knowledge base through an MCP server. There are two ways to set it up:

| | Standalone MCP | Claude Code Plugin |
|---|---|---|
| Vault search | Yes | Yes |
| PostgreSQL tools | Yes | Yes |
| Note creation/editing | No | Yes |
| Works in Claude Desktop | Yes | No |
| Works in Claude Code | Yes | Yes |
| Setup | Manual MCP config | `claude plugin install` |

The **standalone MCP** setup works with both Claude Desktop and Claude Code. The **Claude Code plugin** wraps the same MCP server and adds the `obsidian-notes` skill for writing notes directly to your vault.

## Install the plugin

**For development** (per-session, no install needed):

```bash
claude --plugin-dir /path/to/mnemolith
```

Use `/reload-plugins` inside the session to pick up changes without restarting.

**For persistent install**, register the repo as a marketplace first, then install:

```bash
claude plugin marketplace add /path/to/mnemolith
claude plugin install mnemolith@mnemolith
```

Or interactively: inside a Claude Code session, run `/plugin`, go to the **Discover** tab, and install from there.

Both methods auto-register the MCP server and the `obsidian-notes` skill. No manual MCP configuration needed.

To update to the last version of the plugin later on:

```bash
claude plugin update mnemolith@mnemolith
```

## Configuration

The plugin's MCP server reads the `.env` file from the mnemolith project root — the same one used by the CLI. Make sure you've configured it per [Getting Started](getting-started.md#2-configure-environment) before installing the plugin.

The services (Qdrant, PostgreSQL) must be running (`docker compose up -d`).

## Searching your vault

Once the plugin is installed, you can ask Claude questions in natural language and it will search your indexed Obsidian notes to answer them:

- **"What do I know about sourdough fermentation?"** — finds relevant notes
- **"Summarize my meeting notes from last week"** — searches and synthesizes
- **"What did I write about project X?"** — recalls your own thinking
- **"Find my notes related to stoicism"** — semantic search, not just keyword matching

Claude uses semantic similarity to find matches, so you don't need exact keywords — asking about "bread recipes" can surface a note titled "Weekend baking experiments".

Results include a relevance score; low-scoring results (below 0.3 by default) are filtered out.

## Structured data with PostgreSQL

The MCP server exposes five PostgreSQL tools that Claude can use on your behalf. You don't need to write SQL — just ask in natural language:

- **"Create a table to track my habits"** — Claude creates the schema for you
- **"Add 'morning run' to my habits"** — inserts a row
- **"Show me my habits for this week"** — queries the table
- **"Mark today's run as done"** — updates data
- **"What tables do I have?"** — lists existing tables

Under the hood, Claude picks the right tool (`pg_create_table`, `pg_mutate`, `pg_query`, etc.). Queries are read-only; mutations go through a separate tool. DDL is restricted to table-level operations for safety.

You can also browse your PostgreSQL data directly via CloudBeaver at [http://localhost:8978](http://localhost:8978).

See [How It Works — PostgreSQL backend](how-it-works.md#postgresql-backend) for the full list of tools and their constraints.

## Creating and editing notes

The `obsidian-notes` skill lets Claude write directly to your vault. You can trigger it naturally:

- **"Make a note about this conversation"** — distills key insights into a vault note
- **"Save this to my vault"** — persists information from the current session
- **"Create a note about X"** — writes a new note on a topic
- **"Update my note on Y"** — edits an existing note

Claude will:

1. Check your vault's folder structure and place the note appropriately
2. Use proper Obsidian formatting (frontmatter, `[[wiki-links]]`, `#tags`)
3. Match your language (the vault is bilingual French/English)
4. Search for related notes and add wiki-links when relevant

## Using both backends together

Claude can bridge both backends in a single conversation. For example, if you track `ASML` in a PostgreSQL `companies` table and have investment research in `Companies/ASML.md`, asking "what's my thesis on ASML?" will pull from both sources automatically.

A good rule of thumb:

| Data type | Backend | Examples |
|---|---|---|
| Structured: fields, states, numbers | PostgreSQL | Portfolio holdings, habit tracker, todo list |
| Unstructured: prose, research, thinking | Obsidian vault | Company research, meeting notes, journal |

For ambiguous queries, Claude checks both.

## Standalone MCP setup

If you don't need note creation, or if you use Claude Desktop, you can configure the MCP server directly without the plugin.

### Claude Desktop

Add the following to your MCP configuration file:

- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "mnemolith": {
      "command": "uv",
      "args": ["run", "--directory", "/absolute/path/to/mnemolith", "mnemolith-mcp"]
    }
  }
}
```

Replace `/absolute/path/to/mnemolith` with the actual path to your mnemolith clone. Restart Claude Desktop after editing the config.

### Claude Code

```bash
claude mcp add mnemolith -- uv run --directory /absolute/path/to/mnemolith mnemolith-mcp
```

Or manually create/edit `.mcp.json` in your project root:

```json
{
  "mcpServers": {
    "mnemolith": {
      "command": "uv",
      "args": ["run", "--directory", "/absolute/path/to/mnemolith", "mnemolith-mcp"]
    }
  }
}
```

### Verifying it works

Ask Claude something about your notes. In Claude Code, you can also check that the server is registered:

```bash
claude mcp list
```

## Troubleshooting

**"Collection not found" error** — you haven't indexed your vault yet. Run `uv run mnemolith index`.

**Server not appearing in Claude** — check that the path in your MCP config is absolute, make sure `uv` is in your PATH, and restart Claude after config changes.

**Search returns no results** — verify Qdrant is running (`curl http://localhost:6333`), re-index after adding new notes, and try different query phrasing.
