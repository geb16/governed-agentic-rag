"""Ingest the integrity-checked knowledge corpus into configured Qdrant storage."""

from app.core.config import get_settings
from app.rag.ingest import ingest


def main() -> None:
    """Load validated settings, ingest approved chunks, and report the indexed count."""
    count = ingest(get_settings())
    print(f"Indexed {count} knowledge chunks.")


if __name__ == "__main__":
    main()
