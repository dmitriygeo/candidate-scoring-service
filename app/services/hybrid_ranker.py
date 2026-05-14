"""
Гибридный ранкер: bi-encoder + cross-encoder + TF-IDF + HistGradientBoostingClassifier.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import joblib
import numpy as np
from loguru import logger
from sklearn.preprocessing import normalize

from config import REPO_ROOT, settings
from app.services.hybrid_ranker_features import clean_text, vector_for_pair


class HybridRanker:
    """загрузка моделей HF и мгновенная загрузка sklearn/joblib."""

    def __init__(self, artifact_dir: Path):
        self._dir = Path(artifact_dir)
        self._meta: Dict[str, Any] = {}
        self._tfidf = None
        self._hgb = None
        self._feature_names: List[str] = []
        self._bi = None
        self._cross = None
        self._batch = 16
        self._load_sklearn_artifacts()

    def _load_sklearn_artifacts(self) -> None:
        meta_path = self._dir / "metadata.json"
        if not meta_path.is_file():
            raise FileNotFoundError(f"Нет metadata.json в {self._dir}")
        with open(meta_path, encoding="utf-8") as f:
            self._meta = json.load(f)
        self._feature_names = list(self._meta["feature_names"])
        self._tfidf = joblib.load(self._dir / "tfidf.joblib")
        self._hgb = joblib.load(self._dir / "hgb.joblib")
        logger.info(
            "HybridRanker: загружены TF-IDF и HGB, признаков: {}",
            len(self._feature_names),
        )

    def _ensure_transformers(self) -> None:
        if self._bi is not None and self._cross is not None:
            return
        from sentence_transformers import SentenceTransformer, CrossEncoder

        bi_name = self._meta.get(
            "bi_model", "intfloat/multilingual-e5-base"
        )
        cross_name = self._meta.get(
            "cross_model", "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"
        )
        logger.info("HybridRanker: загрузка bi-encoder {} …", bi_name)
        self._bi = SentenceTransformer(bi_name)
        logger.info("HybridRanker: загрузка cross-encoder {} …", cross_name)
        self._cross = CrossEncoder(cross_name, num_labels=1)

    @property
    def is_ready(self) -> bool:
        return self._hgb is not None and self._tfidf is not None

    def score_batch(
        self, resume_texts: List[str], vacancy_texts: List[str]
    ) -> np.ndarray:
        """Вероятность класса 1 для каждой пары (одинаковая длина списков)."""
        self._ensure_transformers()
        n = len(resume_texts)
        if len(vacancy_texts) != n:
            raise ValueError("resume_texts и vacancy_texts должны быть одной длины")

        rt = [clean_text(t) for t in resume_texts]
        vt = [clean_text(t) for t in vacancy_texts]

        q_emb = self._bi.encode(
            [f"query: {r}" for r in rt],
            convert_to_numpy=True,
            normalize_embeddings=True,
            batch_size=self._batch,
            show_progress_bar=False,
        )
        d_emb = self._bi.encode(
            [f"passage: {v}" for v in vt],
            convert_to_numpy=True,
            normalize_embeddings=True,
            batch_size=self._batch,
            show_progress_bar=False,
        )
        bi = np.sum(q_emb * d_emb, axis=1).astype(np.float64)

        pairs = list(zip(rt, vt))
        cross_raw = self._cross.predict(
            pairs, batch_size=min(32, max(8, self._batch)), show_progress_bar=False
        )
        cross = np.asarray(cross_raw, dtype=np.float64).reshape(-1)

        a = self._tfidf.transform(rt)
        b = self._tfidf.transform(vt)
        an = normalize(a)
        bn = normalize(b)
        tfidf = np.asarray(an.multiply(bn).sum(axis=1)).ravel().astype(np.float64)

        rows = [
            vector_for_pair(rt[i], vt[i], bi[i], cross[i], tfidf[i], self._feature_names)
            for i in range(n)
        ]
        x = np.asarray(rows, dtype=np.float64)
        proba = self._hgb.predict_proba(x)[:, 1]
        return proba


_hybrid_singleton: Optional[HybridRanker] = None
_hybrid_failed: bool = False


def hybrid_artifact_dir() -> Path:
    raw = settings.HYBRID_RANKER_DIR
    if raw:
        return Path(raw)
    return REPO_ROOT / "artifacts" / "hybrid_ranker"


def get_hybrid_ranker() -> Optional[HybridRanker]:
    global _hybrid_singleton, _hybrid_failed
    if not settings.HYBRID_RANKER_ENABLED:
        return None
    if _hybrid_failed:
        return None
    if _hybrid_singleton is not None:
        return _hybrid_singleton
    d = hybrid_artifact_dir()
    need = [d / "metadata.json", d / "tfidf.joblib", d / "hgb.joblib"]
    if not all(p.is_file() for p in need):
        logger.warning(
            "HybridRanker отключён: не все файлы в {} (нужны metadata.json, tfidf.joblib, hgb.joblib)",
            d,
        )
        _hybrid_failed = True
        return None
    try:
        _hybrid_singleton = HybridRanker(d)
    except Exception as e:
        logger.exception("Не удалось загрузить HybridRanker: {}", e)
        _hybrid_failed = True
        return None
    return _hybrid_singleton
