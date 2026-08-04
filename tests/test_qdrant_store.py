import warnings
from unittest.mock import MagicMock, patch

from mnemolith.qdrant_store import _build_client


def _emit_insecure_warning(**_kwargs):
    warnings.warn("Api key is used with an insecure connection.", UserWarning, stacklevel=2)
    return MagicMock()


@patch("mnemolith.qdrant_store.QdrantClient", side_effect=_emit_insecure_warning)
def test_insecure_warning_muted_on_loopback_only(mock_client):
    """The warning is noise on 127.0.0.1 (it would repeat on every cron run) but real for a remote host."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        _build_client("http://localhost:6333", "secret")
    assert caught == []

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        _build_client("http://qdrant.example.com:6333", "secret")
    assert len(caught) == 1

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        _build_client("http://localhost:6333", None)  # no key, nothing to leak
    assert len(caught) == 1
