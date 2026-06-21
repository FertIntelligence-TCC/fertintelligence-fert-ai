import json
import re
from pathlib import Path
from collections import Counter

from app.rag.embeddings.hash_provider import HashEmbeddingProvider

import faiss

BASE_DIR = Path(__file__).resolve().parents[2]
VECTORSTORE_DIR = BASE_DIR / "vectorstore"
INDEX_PATH = VECTORSTORE_DIR / "index.faiss"
DOCUMENTS_PATH = VECTORSTORE_DIR / "documents.json"

embedding_provider = HashEmbeddingProvider()


def _tokenize(text: str) -> list[str]:
    return embedding_provider.tokenize(text)


def _embed(text: str):
    return embedding_provider.embed_text(text)

def _load_documents() -> list[dict]:
    if not DOCUMENTS_PATH.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {DOCUMENTS_PATH}")

    with DOCUMENTS_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def _get_text(doc: dict) -> str:
    return (
        doc.get("text")
        or doc.get("content")
        or doc.get("chunk")
        or ""
    )


def _clean_preview(text: str, max_chars: int = 700) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_chars]


def _lexical_score(question: str, text: str) -> tuple[float, list[str]]:
    q_tokens = _tokenize(question)
    t_tokens = _tokenize(text)

    if not q_tokens or not t_tokens:
        return 0.0, []

    q_counter = Counter(q_tokens)
    t_set = set(t_tokens)

    matched = sorted([token for token in q_counter if token in t_set])
    score = len(matched) / max(len(set(q_tokens)), 1)

    phrase_bonus = 0.0
    q_norm = " ".join(q_tokens)
    t_norm = " ".join(t_tokens)

    important_phrases = [
        "saturacao bases",
        "calagem",
        "adubacao",
        "gessagem",
        "analise solo",
        "fertilidade solo",
        "sodio trocavel",
        "pst",
    ]

    for phrase in important_phrases:
        if phrase in q_norm and phrase in t_norm:
            phrase_bonus += 0.25

    return score + phrase_bonus, matched


def retrieve_sources(question: str, top_k: int = 5) -> list[dict]:
    if not question or not question.strip():
        return []

    if not INDEX_PATH.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {INDEX_PATH}")

    index = faiss.read_index(str(INDEX_PATH))
    documents = _load_documents()

    top_k = max(1, min(int(top_k), 20))
    search_k = min(max(top_k * 12, 30), len(documents))

    query_vector = _embed(question)
    faiss_scores, indices = index.search(query_vector, search_k)

    candidates = []

    for faiss_score, idx in zip(faiss_scores[0], indices[0]):
        if idx < 0 or idx >= len(documents):
            continue

        doc = documents[idx]
        text = _get_text(doc)

        lexical, matched_terms = _lexical_score(question, text)

        combined_score = (float(faiss_score) * 0.65) + (lexical * 0.35)

        candidates.append(
            {
                "source": doc.get("source") or doc.get("file") or doc.get("filename"),
                "page": doc.get("page"),
                "score": combined_score,
                "faiss_score": float(faiss_score),
                "lexical_score": lexical,
                "matched_terms": matched_terms,
                "preview": _clean_preview(text),
            }
        )

    candidates.sort(key=lambda item: item["score"], reverse=True)

    return candidates[:top_k]
