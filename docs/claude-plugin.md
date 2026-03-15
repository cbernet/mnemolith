# Claude Code Plugin

Mnemolith is also available as a **Claude Code plugin** that bundles two features:

- **MCP server** — semantic search over your vault (same as standalone MCP setup)
- **Obsidian notes skill** — lets Claude create and edit notes directly in your vault

The MCP server works in both Claude Desktop and Claude Code. The skill is Claude Code only.

## Install the plugin

From a local clone:

```bash
claude plugin install /path/to/mnemolith
```

This auto-registers both the MCP server and the `obsidian-notes` skill. No manual MCP configuration needed.

## Configuration

The plugin's MCP server reads the `.env` file from the mnemolith project root — the same one used by the CLI. Make sure you've configured it per [Getting Started](getting-started.md#2-configure-environment) before installing the plugin.

The services (Qdrant, PostgreSQL) must be running (`docker compose up -d`).

## The obsidian-notes skill

Once the plugin is installed, Claude Code can create and edit notes in your vault. You can trigger it naturally:

- "Make a note about this conversation"
- "Save this to my vault"
- "Create a note about X"
- "Update my note on Y"

Claude will:

1. Check your vault's folder structure and place the note appropriately
2. Use proper Obsidian formatting (frontmatter, `[[wiki-links]]`, `#tags`)
3. Match your language (the vault is bilingual French/English)
4. Link to related existing notes when relevant

## Plugin vs standalone MCP

| Feature | Standalone MCP | Plugin |
|---|---|---|
| Semantic search | Yes | Yes |
| Note creation/editing | No | Yes (Claude Code only) |
| Setup | Manual MCP config | `claude plugin install` |
| Works in Claude Desktop | Yes | MCP part only |

If you only need search, the [standalone MCP setup](mcp-setup.md) is simpler. If you want Claude to also write notes, use the plugin.
