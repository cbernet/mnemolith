import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path

import yaml

_CHUNK_NAMESPACE = uuid.UUID("00000000-0000-0000-0000-0000000000c0")


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


def chunk_document(doc: Document) -> list[Document]:
    splits = HEADING2_RE.split(doc.content)
    # splits alternates: [intro, heading1, body1, heading2, body2, ...]
    intro = splits[0].strip()
    chunks = []

    if intro:
        chunks.append(Document(
            path=doc.path,
            title=doc.title,
            content=intro,
            frontmatter=doc.frontmatter,
            tags=doc.tags,
            links=doc.links,
        ))

    for i in range(1, len(splits), 2):
        heading = splits[i].strip()
        body = splits[i + 1].strip() if i + 1 < len(splits) else ""
        if not body and not heading:
            continue
        chunks.append(Document(
            path=doc.path,
            title=doc.title,
            content=body,
            frontmatter=doc.frontmatter,
            tags=doc.tags,
            links=doc.links,
            heading=heading,
        ))

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
