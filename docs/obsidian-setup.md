# Obsidian Setup

This guide walks you through installing Obsidian, creating a vault, and backing it up with Git. If you already have a vault with Git set up, skip to [Getting Started](getting-started.md).

## Install Obsidian

Download Obsidian from [obsidian.md](https://obsidian.md/) and install it. It's free for personal use.

## Create a vault

A vault is just a folder of markdown files. When you first open Obsidian, it will ask you to create or open a vault.

- **Create new vault**: pick a name and location on your machine (e.g. `~/Obsidian Vault`)
- **Open existing folder**: if you already have markdown notes, point Obsidian at that folder

That's it — Obsidian creates a hidden `.obsidian/` folder inside for its own config, and everything else is plain `.md` files you own.

## Set up Git for your vault

Backing your vault with a remote Git repository gives you:

- **Version history** for all your notes
- **Backup** in case your machine dies
- **Multi-device sync** (pull on another machine, or use the mobile Git plugin)
- **CI-driven indexing** (you could re-index on push in the future)

### Create a remote repository

1. Go to GitHub and create a **private** repository (your notes are personal)
2. Name it whatever you like (e.g. `obsidian-vault`)
3. Don't initialize it with a README — you'll push from your existing vault

### Initialize Git in your vault

Open a terminal and run:

```bash
cd ~/Obsidian\ Vault   # adjust to your vault path

git init
git remote add origin git@github.com:youruser/obsidian-vault.git

# Create a .gitignore to skip Obsidian's internal caches
cat > .gitignore << 'EOF'
.obsidian/workspace.json
.obsidian/workspace-mobile.json
.obsidian/plugins/obsidian-git/data.json
.trash/
EOF

git add -A
git commit -m "Initial commit"
git push -u origin main
```

### Install the Obsidian Git plugin

The [Obsidian Git](https://github.com/denolehov/obsidian-git) community plugin automates commits and pushes so you don't have to think about it.

1. In Obsidian, go to **Settings > Community plugins**
2. Turn off **Restricted mode** if it's still on
3. Click **Browse**, search for **Obsidian Git**, and install it
4. Enable the plugin

### Configure auto-backup

In **Settings > Community plugins > Obsidian Git**:

| Setting | Recommended value | Why |
|---|---|---|
| Auto backup interval | `10` (minutes) | Frequent enough to never lose much work |
| Auto pull interval | `10` (minutes) | Keeps your vault in sync if you edit from another device |
| Commit message | `vault backup: {{date}}` | Clear and timestamped |
| Push on backup | enabled | So backups reach the remote immediately |

With these settings, Obsidian Git will commit and push every 10 minutes in the background. You can also trigger a manual backup from the command palette (`Ctrl/Cmd+P` > "Obsidian Git: Create backup").

### Verify it works

After the first auto-backup interval (or a manual backup), check your GitHub repo — you should see your notes there.

## Next step

Your vault is ready. Head to [Getting Started](getting-started.md) to set up mnemolith and index it for semantic search.
