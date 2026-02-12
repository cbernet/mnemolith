from second_brain.parser import (
    Document,
    parse_frontmatter,
    extract_links,
    extract_inline_tags,
    parse_vault,
)


def test_parse_frontmatter_basic():
    text = "---\ntags:\n  - python\n---\n# Title\nBody"
    fm, body = parse_frontmatter(text)
    assert fm == {"tags": ["python"]}
    assert body.startswith("# Title")


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
