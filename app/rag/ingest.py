import json
import re
from pathlib import Path

import faiss
import numpy as np
from pypdf import PdfReader

from app.core.config import DOCS_DIR, VECTORSTORE_DIR, CHUNK_SIZE, CHUNK_OVERLAP
from app.rag.embeddings.hash_provider import HashEmbeddingProvider


embedding_provider = HashEmbeddingProvider()


def normalize_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    text = normalize_text(text)

    if not text:
        return []

    chunks = []
    start = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end >= len(text):
            break

        start = max(0, end - overlap)

    return chunks


def extract_pdf_text(pdf_path: Path) -> list[dict]:
    reader = PdfReader(str(pdf_path))
    pages = []

    for page_index, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception as exc:
            print(f"[WARN] Falha ao extrair página {page_index} de {pdf_path.name}: {exc}")
            text = ""

        text = normalize_text(text)

        if text:
            pages.append(
                {
                    "source": pdf_path.name,
                    "page": page_index,
                    "text": text,
                }
            )

    return pages


def build_index() -> None:
    VECTORSTORE_DIR.mkdir(parents=True, exist_ok=True)

    pdf_files = sorted(DOCS_DIR.glob("*.pdf"))

    if not pdf_files:
        raise RuntimeError(f"Nenhum PDF encontrado em: {DOCS_DIR}")

    documents = []

    print(f"[INFO] PDFs encontrados: {len(pdf_files)}")

    for pdf_path in pdf_files:
        print(f"[INFO] Lendo: {pdf_path.name}")
        pages = extract_pdf_text(pdf_path)

        for page in pages:
            chunks = chunk_text(page["text"])

            for chunk_index, chunk in enumerate(chunks, start=1):
                documents.append(
                    {
                        "id": len(documents),
                        "source": page["source"],
                        "page": page["page"],
                        "chunk_index": chunk_index,
                        "text": chunk,
                    }
                )

    if not documents:
        raise RuntimeError("Nenhum texto foi extraído dos PDFs.")

    print(f"[INFO] Chunks gerados: {len(documents)}")
    print(f"[INFO] Dimensão dos embeddings: {embedding_provider.dimension}")

    matrix = np.vstack(
        [
            embedding_provider.embed_text(doc["text"]).reshape(-1)
            for doc in documents
        ]
    ).astype("float32")

    index = faiss.IndexFlatIP(embedding_provider.dimension)
    index.add(matrix)

    faiss.write_index(index, str(VECTORSTORE_DIR / "index.faiss"))

    with open(VECTORSTORE_DIR / "documents.json", "w", encoding="utf-8") as f:
        json.dump(documents, f, ensure_ascii=False, indent=2)

    print("[OK] Índice salvo em vectorstore/index.faiss")
    print("[OK] Metadados salvos em vectorstore/documents.json")


if __name__ == "__main__":
    build_index()
