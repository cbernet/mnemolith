import re
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import yaml

_CHUNK_NAMESPACE = uuid.UUID("00000000-0000-0000-0000-0000000000c0")

# Well under the 8192-token embedding input limit, and just below the vault's p99
# chunk size -- so it only splits the outliers that were drowning the signal.
MAX_CHUNK_TOKENS = 2000

TokenCounter = Callable[[str], int]

# Chars per token measured at 3.55 over this vault, so //3 over-estimates the count.
_CHARS_PER_TOKEN = 3


def _rough_token_count(text: str) -> int:
    return len(text) // _CHARS_PER_TOKEN


def chunk_id(path: str, chunk_index: int) -> str:
    """Stable UUID5 derived from (path, chunk_index). Same input -> same id across runs."""
    return str(uuid.uuid5(_CHUNK_NAMESPACE, f"{path}::{chunk_index}"))


@dataclass
class Document:
    path: str
    title: str
    content: str
    frontmatter: dict = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    links: list[str] = field(default_factory=list)
    heading: str | None = None
    chunk_index: int = 0


FRONTMATTER_RE = re.compile(r"^---\n(.+?)\n---\n?", re.DOTALL)
HEADING2_RE = re.compile(r"^## (.+)$", re.MULTILINE)
WIKI_LINK_RE = re.compile(r"\[\[([^\]]+)\]\]")
INLINE_TAG_RE = re.compile(r"(?<=\s)#([a-zA-Z][\w-]*)")


def parse_frontmatter(text: str) -> tuple[dict, str]:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}, text
    raw_yaml = match.group(1)
    body = text[match.end():]
    try:
        fm = yaml.safe_load(raw_yaml)
    except yaml.YAMLError:
        return {}, text
    if not isinstance(fm, dict):
        return {}, text
    return fm, body


def extract_links(text: str) -> list[str]:
    return WIKI_LINK_RE.findall(text)


def extract_inline_tags(text: str) -> list[str]:
    return INLINE_TAG_RE.findall(text)


def parse_file(filepath: Path, vault_root: Path) -> Document | None:
    text = filepath.read_text(encoding="utf-8")
    if not text.strip():
        return None

    frontmatter, body = parse_frontmatter(text)
    relative_path = str(filepath.relative_to(vault_root))
    title = filepath.stem

    fm_tags = frontmatter.get("tags", []) or []
    inline_tags = extract_inline_tags(body)
    title_words = re.split(r"[-_]", title)
    folder_parts = list(Path(relative_path).parent.parts)
    all_tags = list(dict.fromkeys(fm_tags + inline_tags + title_words + folder_parts))

    links = extract_links(body)

    return Document(
        path=relative_path,
        title=title,
        content=body.strip(),
        frontmatter=frontmatter,
        tags=all_tags,
        links=links,
    )


def _pack(pieces: list[str], sep: str, max_tokens: int, count: TokenCounter) -> list[str]:
    """Merge consecutive pieces into groups of at most max_tokens, rejoined with sep.

    Document order is preserved and nothing is dropped. A single piece larger than
    max_tokens is returned on its own, still oversized -- the caller splits it further
    on a finer separator.
    """
    sep_cost = count(sep)
    out: list[str] = []
    current, current_tokens = "", 0
    for piece in pieces:
        piece_tokens = count(piece)
        extra = piece_tokens + (sep_cost if current else 0)
        if current and current_tokens + extra > max_tokens:
            out.append(current)
            current, current_tokens = piece, piece_tokens
        else:
            current = f"{current}{sep}{piece}" if current else piece
            current_tokens += extra
    if current:
        out.append(current)
    return out


def split_text(
    text: str,
    max_tokens: int = MAX_CHUNK_TOKENS,
    count: TokenCounter = _rough_token_count,
) -> list[str]:
    """Split text into pieces of at most max_tokens, on the coarsest boundary that works.

    Tries paragraphs, then lines, and only slices mid-line for input with no structure
    left to exploit. Returns [text] unchanged when it already fits.
    """
    if count(text) <= max_tokens:
        return [text]

    for sep in ("\n\n", "\n"):
        if sep not in text:
            continue
        pieces = _pack(text.split(sep), sep, max_tokens, count)
        if pieces == [text]:
            continue
        # Each piece is strictly shorter than text, so this recursion terminates.
        result: list[str] = []
        for piece in pieces:
            result.extend(split_text(piece, max_tokens, count))
        return result

    # No structure left to exploit (minified JSON, base64 blob): slice on characters,
    # using this text's own chars-per-token ratio so the width fits any counter.
    ratio = max(1, len(text) // max(1, count(text)))
    width = max(1, max_tokens * ratio)
    return [text[i:i + width] for i in range(0, len(text), width)]


def chunk_document(
    doc: Document,
    max_tokens: int = MAX_CHUNK_TOKENS,
    count: TokenCounter = _rough_token_count,
) -> list[Document]:
    splits = HEADING2_RE.split(doc.content)
    # splits alternates: [intro, heading1, body1, heading2, body2, ...]
    chunks = []

    def add(content: str, heading: str | None) -> None:
        for piece in split_text(content, max_tokens, count):
            chunks.append(Document(
                path=doc.path,
                title=doc.title,
                content=piece,
                frontmatter=doc.frontmatter,
                tags=doc.tags,
                links=doc.links,
                heading=heading,
            ))

    intro = splits[0].strip()
    if intro:
        add(intro, None)

    for i in range(1, len(splits), 2):
        heading = splits[i].strip()
        body = splits[i + 1].strip() if i + 1 < len(splits) else ""
        if not body and not heading:
            continue
        add(body, heading)

    if not chunks:
        chunks.append(doc)

    for i, c in enumerate(chunks):
        c.chunk_index = i
    return chunks


def build_embedding_text(doc: Document) -> str:
    parts = [f"# {doc.title}"]
    if doc.heading:
        parts.append(f"## {doc.heading}")
    parts.append("")
    if doc.tags:
        tag_line = " ".join(f"#{t}" for t in doc.tags)
        parts.extend([tag_line, ""])
    parts.append(doc.content)
    return "\n".join(parts)


def parse_vault(vault_path: str) -> list[Document]:
    root = Path(vault_path)
    documents = []
    for md_file in sorted(root.rglob("*.md")):
        doc = parse_file(md_file, root)
        if doc is not None:
            documents.append(doc)
    return documents
