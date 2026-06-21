import hashlib
import re
import unicodedata

import numpy as np

EMBEDDING_DIM = 1536

STOPWORDS = {
    "a", "o", "os", "as", "um", "uma", "uns", "umas",
    "de", "do", "da", "dos", "das", "em", "no", "na", "nos", "nas",
    "por", "para", "com", "sem", "sobre", "entre",
    "e", "ou", "que", "se", "como", "qual", "quais",
    "é", "sao", "são", "ser", "foi", "sua", "seu", "suas", "seus",
    "isso", "essa", "esse", "esta", "este",
}


class HashEmbeddingProvider:
    @property
    def dimension(self) -> int:
        return EMBEDDING_DIM

    def embed_text(self, text: str) -> np.ndarray:
        vector = np.zeros(self.dimension, dtype="float32")

        for token in self.tokenize(text):
            digest = hashlib.md5(token.encode("utf-8")).hexdigest()
            idx = int(digest, 16) % self.dimension
            vector[idx] += 1.0

        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm

        return vector.reshape(1, -1)

    def tokenize(self, text: str) -> list[str]:
        text = self._strip_accents(text.lower())
        tokens = re.findall(r"[a-z0-9]+", text, flags=re.UNICODE)
        return [token for token in tokens if len(token) > 2 and token not in STOPWORDS]

    @staticmethod
    def _strip_accents(text: str) -> str:
        text = unicodedata.normalize("NFKD", text)
        return "".join(ch for ch in text if not unicodedata.combining(ch))
