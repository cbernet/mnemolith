# MCP Server Setup

Mnemolith includes an MCP (Model Context Protocol) server that lets Claude search your vault through semantic search. This works with both **Claude Desktop** and **Claude Code**.

## Prerequisites

Before setting up the MCP server, make sure you have:

- Indexed your vault (`uv run mnemolith index`) — see [Getting Started](getting-started.md)
- Qdrant running (`docker compose up -d`)
- Your `.env` configured with `OPENAI_API_KEY`

## How it works

The MCP server exposes a `search` tool to Claude. When Claude needs information from your notes, it calls this tool with a natural language query and gets back the most semantically relevant chunks from your vault.

## Setup for Claude Desktop

Add the following to your Claude Desktop MCP configuration file:

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

Replace `/absolute/path/to/mnemolith` with the actual path to your mnemolith clone.

Restart Claude Desktop after editing the config.

## Setup for Claude Code

Add the server to your project's `.mcp.json` or your global MCP settings:

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

## Verifying it works

Once configured, ask Claude something about your notes. For example:

> "Search my vault for notes about project management"

Claude should call the mnemolith search tool and return relevant excerpts from your vault.

In Claude Code, you can also check that the MCP server is registered:

```bash
claude mcp list
```

## Troubleshooting

**"Collection not found" error**

You haven't indexed your vault yet. Run:

```bash
uv run mnemolith index
```

**Server not appearing in Claude**

- Check that the path in your MCP config is absolute and correct
- Make sure `uv` is in your PATH (try running `which uv`)
- Restart Claude Desktop / Claude Code after config changes

**Search returns no results or poor results**

- Verify Qdrant is running: `curl http://localhost:6333`
- Re-index after adding new notes: `uv run mnemolith index`
- Try different query phrasing — semantic search works best with natural language
