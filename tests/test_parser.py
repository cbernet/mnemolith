from mnemolith.parser import (
    Document,
    _pack,
    build_embedding_text,
    chunk_document,
    chunk_id,
    extract_inline_tags,
    extract_links,
    parse_frontmatter,
    parse_vault,
    split_text,
)


# Word-count stand-in for a real tokenizer: deterministic and offline, so chunking
# tests never load a tiktoken vocab.
def word_count(text: str) -> int:
    return len(text.split())


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


def test_chunk_document_assigns_chunk_index():
    doc = Document(
        path="test.md",
        title="test",
        content="Intro.\n\n## A\n\nBody A.\n\n## B\n\nBody B.",
    )
    chunks = chunk_document(doc)
    assert [c.chunk_index for c in chunks] == [0, 1, 2]


def test_chunk_id_stable():
    """Same (path, chunk_index) -> same UUID."""
    assert chunk_id("notes/foo.md", 0) == chunk_id("notes/foo.md", 0)


def test_chunk_id_distinct_for_different_inputs():
    a = chunk_id("notes/foo.md", 0)
    b = chunk_id("notes/foo.md", 1)
    c = chunk_id("notes/bar.md", 0)
    assert len({a, b, c}) == 3


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


def test_pack_groups_consecutive_pieces():
    """Greedy grouping: merge neighbours while they fit, preserving order.

    Budget 10, pieces of 4/3/5/12 words. Separator costs 1, so A+B = 4+3+1 = 8 fits,
    adding C would make 14. D is atomic and oversized, so it comes back as-is.
    """
    a, b, c, d = "w " * 4, "w " * 3, "w " * 5, "w " * 12
    pieces = [a.strip(), b.strip(), c.strip(), d.strip()]
    packed = _pack(pieces, "\n\n", 10, word_count)
    assert packed == [f"{a.strip()}\n\n{b.strip()}", c.strip(), d.strip()]
    assert word_count(packed[-1]) == 12  # oversized atomic piece survives untouched


def test_pack_counts_separator_cost():
    """The separator inserted between merged pieces counts against the budget.

    Uses len() as the counter so the separator has a non-zero cost (a word-count
    tokenizer scores whitespace as 0). Two 5-char pieces plus a 2-char separator is
    12: too big for a budget of 10, and an exact fit for 12.
    """
    piece = "abcde"
    assert _pack([piece, piece], "\n\n", 10, len) == [piece, piece]
    assert _pack([piece, piece], "\n\n", 12, len) == [f"{piece}\n\n{piece}"]


def test_split_text_returns_short_text_unchanged():
    assert split_text("short enough", 10, word_count) == ["short enough"]


def test_split_text_splits_on_paragraphs():
    text = "\n\n".join(["w " * 8, "w " * 8, "w " * 8])
    pieces = split_text(text, 10, word_count)
    assert len(pieces) == 3
    assert all(word_count(p) <= 10 for p in pieces)


def test_split_text_descends_to_lines_when_paragraph_too_big():
    """A single paragraph over budget must be split on its newlines."""
    paragraph = "\n".join(["w " * 6] * 4)
    pieces = split_text(paragraph, 10, word_count)
    assert len(pieces) > 1
    assert all(word_count(p) <= 10 for p in pieces)


def test_split_text_slices_unstructured_text():
    """One giant 'word' has no structure to exploit: slice it on characters.

    Counted with len() so the blob actually exceeds the budget -- a word-count
    tokenizer would score it as a single token and leave it alone.
    """
    blob = "x" * 500
    pieces = split_text(blob, 100, len)
    assert len(pieces) > 1
    assert all(len(p) <= 100 for p in pieces)
    assert "".join(pieces) == blob


def test_split_text_terminates_when_counter_is_inconsistent():
    """A BPE counter can score a whole string above the sum of its parts.

    Packing then rebuilds the original text and makes no progress. The guard must fall
    through to a finer separator instead of recursing forever.
    """
    def inconsistent(text: str) -> int:
        # Only the whole string is over budget; every part packs back into it.
        return 100 if text == "a\n\nb" else 1

    pieces = split_text("a\n\nb", 10, inconsistent)
    assert "".join(pieces) == "a\n\nb"


def test_split_text_preserves_content():
    text = "\n\n".join(f"paragraph {i} " + "w " * 8 for i in range(6))
    pieces = split_text(text, 10, word_count)
    assert "\n\n".join(pieces) == text


def test_chunk_document_caps_long_section():
    """A long ## section yields several chunks, all under budget, all same heading."""
    body = "\n\n".join("w " * 8 for _ in range(6))
    doc = Document(path="test.md", title="test", content=f"## Big\n\n{body}")
    chunks = chunk_document(doc, max_tokens=10, count=word_count)
    assert len(chunks) > 1
    assert all(word_count(c.content) <= 10 for c in chunks)
    assert all(c.heading == "Big" for c in chunks)
    assert [c.chunk_index for c in chunks] == list(range(len(chunks)))
