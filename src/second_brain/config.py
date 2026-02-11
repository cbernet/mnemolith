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
