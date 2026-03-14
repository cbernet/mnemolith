---
name: obsidian-notes
description: Create or edit notes in the user's Obsidian vault. Use this skill whenever the user asks to save, capture, or create a note, or says things like "make a note about this", "save this to my vault", "create an Obsidian note", "note this down", "turn this into a note". Also trigger when the user references their vault, wiki-links, or asks to update existing vault notes. Even if the user just says "note" or "save this", trigger if the context suggests they want to persist information to their knowledge base.
---

# Obsidian Note Creator

The Obsidian vault path is defined by the `OBSIDIAN_VAULT_PATH` environment variable. Before doing anything, read this variable to locate the vault. If it is not set, ask the user to set it.

This is an Obsidian vault — a personal knowledge management system using markdown files. Create or edit notes directly in the vault, respecting its conventions.

## Structure

Check the actual folder structure before placing a note. Respect it; put the note in the best folder. If no folder is a good match, put it at the root of the vault.

## File Format

All content files are markdown (`.md`). When creating or editing notes:

- Use standard markdown syntax, check that the syntax is correct
- Add empty lines before and after blocks
- Do not add an empty line between list items
- Use `[[wiki-style links]]` for linking between notes
- Use tags with `#tag-name` syntax

## Note Structure

Start the note with the title as an H1 heading, then write the front matter block below it:

```
# Note Title

date: 2026-01-24
type: ressources thérapeutiques
tags: #tag-one #tag-two
related: [[Existing Note]] [[Another Note]]
```

Do not put the front matter in a code block and do not create YAML properties — that would deactivate the wiki-links. Write it in plain text as shown above.

Then a blank line, followed by the note body.

## When to Use Wiki-Links

Only use `[[wiki-links]]` for actual notes in this vault:

- Use wiki-links to reference other notes that exist or should exist in the vault
- **Do NOT use wiki-links for**: author names in frontmatter (use plain text), external references, URLs, people outside the vault, generic terms that aren't note files, metadata fields unless explicitly linking to an existing note

## Resolving Wiki-Links

Wiki-links are vault-wide references, not path-based. When encountering `[[Note Name]]`, do NOT assume the target is in the same directory — Obsidian searches the entire vault. To find a link target, search the vault: `find "$OBSIDIAN_VAULT_PATH" -name '*Note Name*.md' -not -path '*/.obsidian/*'`

## Working with Notes

1. Respect the existing folder structure
2. Use clear, descriptive filenames
3. Consider whether new content should be a separate note or added to an existing one
4. Search for related notes and propose wiki-links if they genuinely add value
5. Daily notes follow the format `YYYY-MM-DD.md` in the root directory
6. Match the user's language (the vault is bilingual French/English)
7. Be concise — vault notes should be scannable and useful months later
8. When distilling a conversation, focus on key insights, decisions, and action items
