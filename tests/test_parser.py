from mnemolith.parser import (
    Document,
    parse_frontmatter,
    extract_links,
    extract_inline_tags,
    parse_vault,
    build_embedding_text,
    chunk_document,
)


def test_parse_frontmatter_basic():
    text = "---\ntags:\n  - python\n---\n# Title\nBody"
    fm, body = parse_frontmatter(text)
    assert fm == {"tags": ["python"]}
    assert body.startswith("# Title")


def test_parse_frontmatter_invalid_yaml():
    text = "---\n: [invalid yaml\n---\nBody"
    fm, body = parse_frontmatter(text)
    assert fm == {}
    assert body == text


def test_parse_frontmatter_missing():
    text = "# No frontmatter\nJust text."
    fm, body = parse_frontmatter(text)
    assert fm == {}
    assert body == text


def test_extract_links():
    text = "See [[note-a]] and [[folder/note-b]]."
    assert extract_links(text) == ["note-a", "folder/note-b"]


def test_extract_inline_tags():
    text = "This has #tag-one and #tag2 in it."
    assert extract_inline_tags(text) == ["tag-one", "tag2"]


def test_inline_tags_ignore_headings():
    text = "# Heading\nSome text with #real-tag here."
    tags = extract_inline_tags(text)
    assert "Heading" not in tags
    assert "real-tag" in tags


def test_parse_vault(vault_path):
    docs = parse_vault(vault_path)
    assert all(isinstance(d, Document) for d in docs)
    paths = [d.path for d in docs]
    assert "empty.md" not in paths
    assert "simple.md" in paths


def test_parse_vault_frontmatter_tags(vault_path):
    docs = parse_vault(vault_path)
    simple = next(d for d in docs if d.title == "simple")
    assert "python" in simple.tags
    assert "testing" in simple.tags


def test_parse_vault_wiki_links(vault_path):
    docs = parse_vault(vault_path)
    wl = next(d for d in docs if d.title == "wiki-links")
    assert "simple" in wl.links
    assert "french-note" in wl.links
    assert "nonexistent-note" in wl.links


def test_parse_vault_french_content(vault_path):
    docs = parse_vault(vault_path)
    french = next(d for d in docs if d.title == "french-note")
    assert "crêpes" in french.content.lower()
    assert "cuisine" in french.tags


def test_parse_vault_nested(vault_path):
    docs = parse_vault(vault_path)
    deep = next(d for d in docs if d.title == "deep-note")
    assert deep.path == "nested/deep-note.md"
    assert "nested" in deep.tags


def test_parse_vault_inline_tags(vault_path):
    docs = parse_vault(vault_path)
    it = next(d for d in docs if d.title == "inline-tags")
    assert "frontmatter-tag" in it.tags
    assert "inline-tag" in it.tags
    assert "another-tag" in it.tags


def test_parse_vault_no_frontmatter(vault_path):
    docs = parse_vault(vault_path)
    nf = next(d for d in docs if d.title == "no-frontmatter")
    assert nf.frontmatter == {}
    assert "Just Content" in nf.content


def test_parse_vault_title_words_in_tags(vault_path):
    docs = parse_vault(vault_path)
    deep = next(d for d in docs if d.title == "deep-note")
    assert "deep" in deep.tags
    assert "note" in deep.tags


def test_parse_vault_folder_parts_in_tags(vault_path):
    docs = parse_vault(vault_path)
    deep = next(d for d in docs if d.title == "deep-note")
    # "nested" comes from both frontmatter and folder — should be present
    assert "nested" in deep.tags
    # root-level file should not have folder tags
    simple = next(d for d in docs if d.title == "simple")
    assert "simple" in simple.tags  # title word


def test_build_embedding_text_with_folders():
    doc = Document(
        path="projects/machine-learning/note.md",
        title="note",
        content="Some body content.",
        tags=["note", "projects", "machine-learning"],
    )
    text = build_embedding_text(doc)
    assert text == "# note\n\n#note #projects #machine-learning\n\nSome body content."


def test_build_embedding_text_root_level():
    doc = Document(
        path="simple.md",
        title="simple",
        content="Body here.",
        tags=["simple"],
    )
    text = build_embedding_text(doc)
    assert text == "# simple\n\n#simple\n\nBody here."


def test_build_embedding_text_with_heading():
    doc = Document(
        path="test.md",
        title="My Note",
        content="Section body.",
        tags=["tag1"],
        heading="Important Section",
    )
    text = build_embedding_text(doc)
    assert text == "# My Note\n## Important Section\n\n#tag1\n\nSection body."


def test_chunk_document_with_headings():
    doc = Document(
        path="test.md",
        title="test",
        content="Intro text.\n\n## Section A\n\nBody A.\n\n## Section B\n\nBody B.",
        tags=["tag1"],
        links=["link1"],
    )
    chunks = chunk_document(doc)
    assert len(chunks) == 3
    # Intro chunk
    assert chunks[0].heading is None
    assert chunks[0].content == "Intro text."
    assert chunks[0].path == "test.md"
    assert chunks[0].tags == ["tag1"]
    assert chunks[0].links == ["link1"]
    # Section A
    assert chunks[1].heading == "Section A"
    assert chunks[1].content == "Body A."
    assert chunks[1].path == "test.md"
    # Section B
    assert chunks[2].heading == "Section B"
    assert chunks[2].content == "Body B."


def test_chunk_document_no_headings():
    doc = Document(
        path="test.md",
        title="test",
        content="Just plain text, no headings.",
        tags=["tag1"],
    )
    chunks = chunk_document(doc)
    assert len(chunks) == 1
    assert chunks[0].heading is None
    assert chunks[0].content == "Just plain text, no headings."


def test_chunk_document_no_intro():
    doc = Document(
        path="test.md",
        title="test",
        content="## Only Section\n\nContent here.",
    )
    chunks = chunk_document(doc)
    assert len(chunks) == 1
    assert chunks[0].heading == "Only Section"
    assert chunks[0].content == "Content here."


def test_chunk_document_preserves_h3():
    """### headings are NOT split points — they stay with their parent ## section."""
    doc = Document(
        path="test.md",
        title="test",
        content="## Parent\n\nIntro.\n\n### Sub\n\nSub content.",
    )
    chunks = chunk_document(doc)
    assert len(chunks) == 1
    assert chunks[0].heading == "Parent"
    assert "### Sub" in chunks[0].content
