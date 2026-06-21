from abc import ABC, abstractmethod

import numpy as np


class EmbeddingProvider(ABC):
    @property
    @abstractmethod
    def dimension(self) -> int:
        pass

    @abstractmethod
    def embed_text(self, text: str) -> np.ndarray:
        pass
