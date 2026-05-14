from typing import List, Optional, Dict, Any, Union
import numpy as np
from dataclasses import dataclass

from loguru import logger

from config import settings


@dataclass
class EmbeddingResult:
    """Результат одной кодировки."""
    embedding: np.ndarray
    text: str
    model_name: str
    dimension: int


class EmbeddingService:
    """Кодирование текстов в векторы; кэш в памяти процесса."""

    def __init__(
        self,
        model_name: Optional[str] = None,
        device: Optional[str] = None
    ):
        self.model_name = model_name or settings.EMBEDDING_MODEL
        self._model = None
        self._device = device
        self._cache: Dict[str, np.ndarray] = {}

    @property
    def model(self):
        """Ленивая загрузка SentenceTransformer."""
        if self._model is None:
            self._load_model()
        return self._model

    def _load_model(self):
        """Загрузить модель sentence-transformers."""
        try:
            from sentence_transformers import SentenceTransformer

            logger.info(f"Загрузка модели эмбеддингов: {self.model_name}")

            self._model = SentenceTransformer(
                self.model_name,
                device=self._device
            )

            logger.info(
                f"Модель загружена. Размерность: {self._model.get_sentence_embedding_dimension()}"
            )

        except Exception as e:
            logger.error(f"Ошибка загрузки модели: {e}")
            raise

    @property
    def dimension(self) -> int:
        """Размерность вектора модели."""
        return self.model.get_sentence_embedding_dimension()

    def encode(
        self,
        text: Union[str, List[str]],
        normalize: bool = True,
        use_cache: bool = True
    ) -> np.ndarray:
        """Один текст или батч; при ``normalize`` — L2; ``use_cache`` — кэш по хэшу текста."""
        if isinstance(text, str):
            texts = [text]
            single = True
        else:
            texts = text
            single = False

        embeddings = []
        texts_to_encode = []
        indices_to_encode = []

        for i, t in enumerate(texts):
            cache_key = self._get_cache_key(t)

            if use_cache and cache_key in self._cache:
                embeddings.append((i, self._cache[cache_key]))
            else:
                texts_to_encode.append(t)
                indices_to_encode.append(i)

        if texts_to_encode:
            new_embeddings = self.model.encode(
                texts_to_encode,
                normalize_embeddings=normalize,
                show_progress_bar=len(texts_to_encode) > 10
            )

            for idx, (text_idx, emb) in enumerate(zip(indices_to_encode, new_embeddings)):
                cache_key = self._get_cache_key(texts_to_encode[idx])

                if use_cache:
                    self._cache[cache_key] = emb

                embeddings.append((text_idx, emb))

        embeddings.sort(key=lambda x: x[0])
        result = np.array([e[1] for e in embeddings])

        if single:
            return result[0]

        return result

    def _get_cache_key(self, text: str) -> str:
        """Ключ кэша по MD5 текста."""
        import hashlib
        return hashlib.md5(text.encode()).hexdigest()

    def cosine_similarity(
        self,
        embedding1: np.ndarray,
        embedding2: np.ndarray
    ) -> float:
        """Скалярное произведение (для L2-нормированных векторов = косинус)."""
        return float(np.dot(embedding1, embedding2))

    def cosine_similarity_batch(
        self,
        query_embedding: np.ndarray,
        embeddings: np.ndarray
    ) -> np.ndarray:
        """Сходство запроса (1D) с каждой строкой матрицы ``embeddings``."""
        return np.dot(embeddings, query_embedding)

    def find_most_similar(
        self,
        query: Union[str, np.ndarray],
        candidates: Union[List[str], np.ndarray],
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """Top-k по косинусу: ``query`` и элементы ``candidates`` — строки или уже эмбеддинги."""
        if isinstance(query, str):
            query_embedding = self.encode(query)
        else:
            query_embedding = query

        if isinstance(candidates, list) and isinstance(candidates[0], str):
            candidate_embeddings = self.encode(candidates)
        else:
            candidate_embeddings = candidates

        similarities = self.cosine_similarity_batch(query_embedding, candidate_embeddings)

        top_indices = np.argsort(similarities)[::-1][:top_k]

        results = []
        for idx in top_indices:
            results.append({
                "index": int(idx),
                "similarity": float(similarities[idx])
            })

        return results

    def create_vacancy_embedding(
        self,
        title: str,
        description: Optional[str] = None,
        skills: Optional[List[str]] = None,
        company: Optional[str] = None
    ) -> np.ndarray:
        """Текст вакансии из полей → эмбеддинг."""
        parts = [f"Вакансия: {title}"]

        if company:
            parts.append(f"Компания: {company}")

        if skills:
            parts.append(f"Навыки: {', '.join(skills)}")

        if description:
            desc = description[:1000] if len(description) > 1000 else description
            parts.append(f"Описание: {desc}")

        text = "\n".join(parts)

        return self.encode(text)

    def build_resume_embedding_text(
        self,
        position_title: Optional[str] = None,
        skills: Optional[List[str]] = None,
        experience_summary: Optional[str] = None,
        about: Optional[str] = None,
    ) -> str:
        """Текст для резюме (тот же, что в ``create_resume_embedding``)."""
        parts: List[str] = []
        if position_title:
            parts.append(f"Должность: {position_title}")
        if skills:
            parts.append(f"Навыки: {', '.join(skills)}")
        if experience_summary:
            parts.append(f"Опыт: {experience_summary}")
        if about:
            about_text = about[:500] if len(about) > 500 else about
            parts.append(f"О себе: {about_text}")
        return "\n".join(parts) if parts else "Резюме без описания"

    def create_resume_embedding(
        self,
        position_title: Optional[str] = None,
        skills: Optional[List[str]] = None,
        experience_summary: Optional[str] = None,
        about: Optional[str] = None
    ) -> np.ndarray:
        """Эмбеддинг резюме из полей профиля."""
        text = self.build_resume_embedding_text(
            position_title=position_title,
            skills=skills,
            experience_summary=experience_summary,
            about=about,
        )
        return self.encode(text)

    def clear_cache(self):
        """Сбросить in-memory кэш."""
        self._cache.clear()
        logger.info("Кэш эмбеддингов очищен")


class VectorIndex:
    """Поиск ближайших соседей: FAISS IndexFlatIP или fallback на numpy."""

    def __init__(
        self,
        dimension: int,
        use_gpu: bool = False
    ):
        self.dimension = dimension
        self.use_gpu = use_gpu

        self._index = None
        self._ids: List[Any] = []

        self._build_index()

    def _build_index(self):
        """Инициализация FAISS или отключение при отсутствии пакета."""
        try:
            import faiss

            self._index = faiss.IndexFlatIP(self.dimension)

            if self.use_gpu:
                try:
                    res = faiss.StandardGpuResources()
                    self._index = faiss.index_cpu_to_gpu(res, 0, self._index)
                    logger.info("FAISS использует GPU")
                except Exception:
                    logger.warning("GPU недоступен, используется CPU")

            logger.info(f"FAISS индекс создан. Размерность: {self.dimension}")

        except ImportError:
            logger.warning("FAISS не установлен, используется numpy fallback")
            self._index = None

    def add(
        self,
        embeddings: np.ndarray,
        ids: List[Any]
    ):
        """Добавить векторы и внешние ``ids``."""
        if len(embeddings) != len(ids):
            raise ValueError("Количество эмбеддингов должно совпадать с количеством ID")

        embeddings = np.ascontiguousarray(embeddings.astype('float32'))

        if self._index is not None:
            self._index.add(embeddings)

        self._ids.extend(ids)

        logger.debug(f"Добавлено {len(ids)} эмбеддингов в индекс")

    def search(
        self,
        query: np.ndarray,
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """Top-k соседей по внутреннему произведению (нормированные векторы ≈ косинус)."""
        if not self._ids:
            return []

        query = np.ascontiguousarray(query.reshape(1, -1).astype('float32'))

        if self._index is not None:
            distances, indices = self._index.search(query, min(top_k, len(self._ids)))

            results = []
            for dist, idx in zip(distances[0], indices[0]):
                if idx >= 0:
                    results.append({
                        "id": self._ids[idx],
                        "similarity": float(dist),
                        "index": int(idx)
                    })

            return results

        all_embeddings = self._get_all_embeddings()
        if all_embeddings is None:
            return []

        similarities = np.dot(all_embeddings, query.flatten())
        top_indices = np.argsort(similarities)[::-1][:top_k]

        results = []
        for idx in top_indices:
            results.append({
                "id": self._ids[idx],
                "similarity": float(similarities[idx]),
                "index": int(idx)
            })

        return results

    def _get_all_embeddings(self) -> Optional[np.ndarray]:
        """Восстановление матрицы из FAISS (только для fallback-пути)."""
        if self._index is not None and hasattr(self._index, 'reconstruct_n'):
            return self._index.reconstruct_n(0, len(self._ids))
        return None

    def __len__(self) -> int:
        return len(self._ids)

    def clear(self):
        """Пересоздать индекс и очистить id."""
        self._build_index()
        self._ids.clear()
