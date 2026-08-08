from app.core.config import get_settings
from app.rag.ingest import ingest


# A Standalone script to ingest knowledge base chunks into the vector store.
def main() -> None:
    count = ingest(get_settings())
    print(f"Indexed {count} knowledge chunks.")


if __name__ == "__main__":
    main()
