import json
import re
import hashlib
from pathlib import Path

import faiss
import numpy as np

BASE_DIR = Path(__file__).resolve().parents[2]
VECTORSTORE_DIR = BASE_DIR / "vectorstore"
INDEX_PATH = VECTORSTORE_DIR / "index.faiss"
DOCUMENTS_PATH = VECTORSTORE_DIR / "documents.json"

EMBEDDING_DIM = 1536


def _tokenize(text: str) -> list[str]:
    return re.findall(r"\w+", text.lower(), flags=re.UNICODE)


def _embed(text: str) -> np.ndarray:
    vector = np.zeros(EMBEDDING_DIM, dtype="float32")

    for token in _tokenize(text):
        digest = hashlib.md5(token.encode("utf-8")).hexdigest()
        idx = int(digest, 16) % EMBEDDING_DIM
        vector[idx] += 1.0

    norm = np.linalg.norm(vector)
    if norm > 0:
        vector = vector / norm

    return vector.reshape(1, -1)


def _load_documents() -> list[dict]:
    if not DOCUMENTS_PATH.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {DOCUMENTS_PATH}")

    with DOCUMENTS_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def retrieve_sources(question: str, top_k: int = 5) -> list[dict]:
    if not INDEX_PATH.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {INDEX_PATH}")

    index = faiss.read_index(str(INDEX_PATH))
    documents = _load_documents()

    query_vector = _embed(question)
    scores, indices = index.search(query_vector, top_k)

    sources = []

    for score, idx in zip(scores[0], indices[0]):
        if idx < 0 or idx >= len(documents):
            continue

        doc = documents[idx]

        text = (
            doc.get("text")
            or doc.get("content")
            or doc.get("chunk")
            or ""
        )

        sources.append(
            {
                "source": doc.get("source") or doc.get("file") or doc.get("filename"),
                "page": doc.get("page"),
                "score": float(score),
                "preview": text[:500].replace("\n", " ").strip(),
            }
        )

    return sources
