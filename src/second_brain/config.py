import os


def get_vault_path() -> str:
    """Return the Obsidian vault path from OBSIDIAN_VAULT_PATH env var."""
    vault_path = os.environ.get("OBSIDIAN_VAULT_PATH")
    if not vault_path:
        raise EnvironmentError(
            "OBSIDIAN_VAULT_PATH environment variable is not set. "
            "Set it to the absolute path of your Obsidian vault."
        )
    return vault_path


def get_qdrant_url() -> str:
    return os.environ.get("QDRANT_URL", "http://localhost:6333")


def get_collection_name() -> str:
    return os.environ.get("COLLECTION_NAME", "obsidian")


def get_embedding_provider() -> str:
    return os.environ.get("EMBEDDING_PROVIDER", "openai")
