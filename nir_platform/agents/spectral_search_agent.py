"""Spectral Search Agent.

Stores spectral fingerprints in a vector database (Qdrant) so past
analyses can be recalled and compared, and so comparable measurements
already executed can be found for a new spectrum. Falls back to an
in-process numpy cosine-similarity index when Qdrant is unavailable, so
the feature still works in the local dev environment without the Qdrant
container running.

A "spectral fingerprint" is the mean intensity vector normalized to unit
L2 norm, paired with metadata (spectrometer type, wavelength range, Brix
range) so the comparison can surface genuinely comparable measurements
(same instrument, overlapping wavelength range).
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

try:
    from qdrant_client import QdrantClient
    from qdrant_client.http import models as qmodels

    _QDRANT_AVAILABLE = True
except ImportError:  # graceful degrade to in-process numpy index
    qmodels = None
    QdrantClient = None  # type: ignore[assignment]
    _QDRANT_AVAILABLE = False

VECTOR_DIM_HINT = 18  # SparkFun Triad channels; Qdrant collections are
                      # created per-vector-size so different instruments
                      # with different channel counts each get a collection.
COLLECTION_PREFIX = "nir_spectra"


@dataclass
class SearchHit:
    """One comparable measurement found by a similarity search."""

    analysis_id: str
    original_filename: str
    spectrometer_type: str
    similarity: float
    brix_range: Optional[Tuple[float, float]] = None
    quality_score: Optional[float] = None
    upload_date: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "analysis_id": self.analysis_id,
            "original_filename": self.original_filename,
            "spectrometer_type": self.spectrometer_type,
            "similarity": round(float(self.similarity), 4),
            "brix_range": (
                [float(self.brix_range[0]), float(self.brix_range[1])]
                if self.brix_range
                else None
            ),
            "quality_score": (
                float(self.quality_score)
                if self.quality_score is not None
                else None
            ),
            "upload_date": self.upload_date,
        }


@dataclass
class SearchResult:
    """Result of a similarity search."""

    query_analysis_id: Optional[str]
    hits: List[SearchHit] = field(default_factory=list)
    backend: str = "none"  # 'qdrant' | 'numpy' | 'none'
    note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query_analysis_id": self.query_analysis_id,
            "hits": [h.to_dict() for h in self.hits],
            "backend": self.backend,
            "note": self.note,
            "count": len(self.hits),
        }


def _normalize(vector: List[float]) -> np.ndarray:
    v = np.asarray(vector, dtype=float)
    n = float(np.linalg.norm(v))
    if n == 0.0 or not math.isfinite(n):
        # avoid divide-by-zero; return zeros so similarity is 0
        return np.zeros_like(v)
    return v / n


class SpectralSearchAgent:
    """Index and search spectral fingerprints across analyses.

    Backend selection:
      - Qdrant (preferred): persistent across restarts, shared by all
        processes/containers.
      - numpy fallback (in-process): a dict of id -> normalized vector.
        Used when qdrant_client is missing or the Qdrant server is down.
    """

    def __init__(self, qdrant_url: str = "http://localhost:6333") -> None:
        self.qdrant_url = qdrant_url
        self._client: Any = None
        self._numpy_index: Dict[str, Dict[str, Any]] = {}
        self.backend: str = "numpy"
        if _QDRANT_AVAILABLE:
            try:
                self._client = QdrantClient(url=qdrant_url, timeout=10)
                # cheap ping
                self._client.get_collections()
                self.backend = "qdrant"
                logger.info(
                    f"Spectral Search Agent connected to Qdrant at {qdrant_url}")
            except Exception as e:  # server down / refused
                self._client = None
                self.backend = "numpy"
                logger.warning(
                    f"Qdrant unavailable ({e}); using in-process numpy index")
        else:
            logger.info(
                "qdrant_client not installed; using in-process numpy index")
        logger.info("Spectral Search Agent initialized (backend=%s)", self.backend)

    # ------------------------------------------------------------------
    # Collection helpers (Qdrant)
    # ------------------------------------------------------------------
    def _collection_name(self, dim: int) -> str:
        return f"{COLLECTION_PREFIX}_{dim}"

    def _ensure_collection(self, dim: int) -> Optional[str]:
        if self._client is None:
            return None
        name = self._collection_name(dim)
        try:
            cols = [c.name for c in self._client.get_collections().collections]
            if name not in cols:
                self._client.create_collection(
                    collection_name=name,
                    vectors_config=qmodels.VectorParams(
                        size=dim, distance=qmodels.Distance.COSINE),
                )
                logger.info(f"Created Qdrant collection '{name}' (dim={dim})")
            return name
        except Exception as e:
            logger.warning(f"Qdrant ensure_collection failed: {e}")
            return None

    # ------------------------------------------------------------------
    # Indexing
    # ------------------------------------------------------------------
    def is_indexed(self, analysis_id: str) -> bool:
        """Return True if a fingerprint for analysis_id is already stored."""
        return str(analysis_id) in self.indexed_analysis_ids()

    def indexed_analysis_ids(self) -> set:
        """Return the set of analysis_ids already in the index.

        Used by the overview page to skip re-upserting analyses that are
        already indexed, avoiding a full re-index (and its Qdrant PUT
        flood) on every page load. Qdrant scrolls all NIR collections once
        and unions their analysis_id payloads; the numpy backend returns
        its in-process keys.
        """
        ids: set = set()
        if self._client is not None:
            try:
                cols = [c.name for c in self._client.get_collections().collections]
                for name in cols:
                    if not name.startswith(COLLECTION_PREFIX):
                        continue
                    offset = None
                    while True:
                        points, offset = self._client.scroll(
                            collection_name=name,
                            offset=offset,
                            limit=256,
                            with_payload=True,
                            with_vectors=False,
                        )
                        if not points:
                            break
                        for p in points:
                            pl = p.payload or {}
                            aid = pl.get("analysis_id") or str(p.id)
                            if aid:
                                ids.add(str(aid))
                        if offset is None:
                            break
            except Exception:
                pass
        ids.update(str(k) for k in self._numpy_index.keys())
        return ids

    def index_analysis(
        self,
        analysis_id: str,
        intensities: List[float],
        metadata: Optional[Dict[str, Any]] = None,
        original_filename: str = "",
        spectrometer_type: str = "",
        quality_score: Optional[float] = None,
        upload_date: Optional[str] = None,
    ) -> bool:
        """Store a spectral fingerprint for one analysis.

        Returns True on success. The intensity vector is normalized; the
        analysis_id is the point id so the same analysis re-indexing
        overwrites rather than duplicates.
        """
        if not intensities:
            logger.warning(f"index_analysis: empty intensities for {analysis_id}")
            return False
        vec = _normalize(intensities)
        dim = int(vec.shape[0])
        meta = metadata or {}
        brix = meta.get("Brix") or meta.get("brix") or meta.get("BRIX")
        brix_range = None
        if brix:
            try:
                vals = [float(x) for x in brix if x not in (None, "")]
                if vals:
                    brix_range = (min(vals), max(vals))
            except (TypeError, ValueError):
                brix_range = None
        payload = {
            "analysis_id": str(analysis_id),
            "original_filename": original_filename,
            "spectrometer_type": spectrometer_type or meta.get("spectrometer_type", ""),
            "brix_range": (
                [brix_range[0], brix_range[1]] if brix_range else None
            ),
            "quality_score": quality_score,
            "upload_date": upload_date,
        }
        if self.backend == "qdrant" and self._client is not None:
            name = self._ensure_collection(dim)
            if name is None:
                # fall through to numpy index
                pass
            else:
                try:
                    self._client.upsert(
                        collection_name=name,
                        points=[
                            qmodels.PointStruct(
                                id=str(analysis_id),
                                vector=vec.tolist(),
                                payload=payload,
                            )
                        ],
                    )
                    return True
                except Exception as e:
                    logger.warning(f"Qdrant upsert failed: {e}")
        # numpy fallback
        self._numpy_index[str(analysis_id)] = {
            "vector": vec,
            "payload": payload,
        }
        return True

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------
    def search_similar(
        self,
        query_intensities: Optional[List[float]] = None,
        query_analysis_id: Optional[str] = None,
        limit: int = 10,
        min_similarity: float = 0.0,
        same_spectrometer_only: bool = False,
    ) -> SearchResult:
        """Find comparable measurements.

        Provide either query_intensities (a spectrum) or query_analysis_id
        (an already-indexed analysis). Returns the most similar past
        analyses by cosine similarity, excluding the query itself.
        """
        if query_intensities is None and query_analysis_id is None:
            return SearchResult(
                query_analysis_id=None, backend=self.backend,
                note="No query provided.")

        # Resolve the query vector + payload
        q_vec: Optional[np.ndarray] = None
        q_payload: Dict[str, Any] = {}
        if query_intensities is not None and query_intensities:
            q_vec = _normalize(query_intensities)
        if query_analysis_id is not None:
            if str(query_analysis_id) in self._numpy_index:
                entry = self._numpy_index[str(query_analysis_id)]
                q_vec = entry["vector"]
                q_payload = entry["payload"]
            elif self.backend == "qdrant" and self._client is not None:
                try:
                    dim = int(q_vec.shape[0]) if q_vec is not None else None
                    if dim is None:
                        # need a dimension to find the collection; skip
                        pass
                    else:
                        name = self._collection_name(dim)
                        pts = self._client.retrieve(
                            collection_name=name, ids=[str(query_analysis_id)],
                            with_payload=True, with_vectors=True)
                        if pts:
                            q_vec = np.asarray(pts[0].vector, dtype=float)
                            q_payload = pts[0].payload or {}
                except Exception as e:
                    logger.warning(f"Qdrant retrieve query failed: {e}")
        if q_vec is None:
            return SearchResult(
                query_analysis_id=query_analysis_id, backend=self.backend,
                note="Could not resolve a query vector.")

        hits: List[SearchHit] = []
        if self.backend == "qdrant" and self._client is not None:
            hits = self._search_qdrant(
                q_vec, query_analysis_id, limit, min_similarity,
                same_spectrometer_only, q_payload)
        if not hits:
            hits = self._search_numpy(
                q_vec, query_analysis_id, limit, min_similarity,
                same_spectrometer_only)
        return SearchResult(
            query_analysis_id=query_analysis_id,
            hits=hits, backend=self.backend,
            note="" if hits else "No comparable measurements found.")

    def _search_qdrant(
        self,
        q_vec: np.ndarray,
        query_analysis_id: Optional[str],
        limit: int,
        min_similarity: float,
        same_spectrometer_only: bool,
        q_payload: Dict[str, Any],
    ) -> List[SearchHit]:
        if self._client is None:
            return []
        dim = int(q_vec.shape[0])
        name = self._collection_name(dim)
        hits: List[SearchHit] = []
        try:
            flt = None
            if same_spectrometer_only and q_payload.get("spectrometer_type"):
                flt = qmodels.Filter(
                    must=[
                        qmodels.FieldCondition(
                            key="spectrometer_type",
                            match=qmodels.MatchValue(
                                value=q_payload["spectrometer_type"]))
                    ]
                )
            res = self._client.search(
                collection_name=name,
                query_vector=q_vec.tolist(),
                limit=limit + 5,
                query_filter=flt,
                with_payload=True,
            )
            for s in res:
                pid = str(s.id)
                if query_analysis_id is not None and pid == str(query_analysis_id):
                    continue
                pl = s.payload or {}
                sim = float(s.score)
                if sim < min_similarity:
                    continue
                br = pl.get("brix_range")
                hits.append(SearchHit(
                    analysis_id=pid,
                    original_filename=pl.get("original_filename", ""),
                    spectrometer_type=pl.get("spectrometer_type", ""),
                    similarity=sim,
                    brix_range=(tuple(br) if br else None),
                    quality_score=pl.get("quality_score"),
                    upload_date=pl.get("upload_date"),
                ))
                if len(hits) >= limit:
                    break
        except Exception as e:
            logger.warning(f"Qdrant search failed: {e}")
        return hits

    def _search_numpy(
        self,
        q_vec: np.ndarray,
        query_analysis_id: Optional[str],
        limit: int,
        min_similarity: float,
        same_spectrometer_only: bool,
    ) -> List[SearchHit]:
        # Determine the query's spectrometer type (for the optional filter).
        q_spectrometer = ""
        if query_analysis_id is not None:
            q_spectrometer = (
                self._numpy_index.get(str(query_analysis_id), {})
                .get("payload", {}).get("spectrometer_type", ""))
        scored: List[Tuple[float, Dict[str, Any]]] = []
        for aid, entry in self._numpy_index.items():
            if query_analysis_id is not None and aid == str(query_analysis_id):
                continue
            v = entry["vector"]
            if v.shape[0] != q_vec.shape[0]:
                # different dimensionality (different instrument) - not comparable
                continue
            sim = float(np.dot(q_vec, v))
            if sim < min_similarity:
                continue
            if (same_spectrometer_only and q_spectrometer
                    and entry["payload"].get("spectrometer_type")
                    and entry["payload"]["spectrometer_type"] != q_spectrometer):
                continue
            scored.append((sim, entry["payload"]))
        scored.sort(key=lambda t: t[0], reverse=True)
        hits: List[SearchHit] = []
        for sim, pl in scored[:limit]:
            br = pl.get("brix_range")
            hits.append(SearchHit(
                analysis_id=pl.get("analysis_id", ""),
                original_filename=pl.get("original_filename", ""),
                spectrometer_type=pl.get("spectrometer_type", ""),
                similarity=sim,
                brix_range=(tuple(br) if br else None),
                quality_score=pl.get("quality_score"),
                upload_date=pl.get("upload_date"),
            ))
        return hits

    # ------------------------------------------------------------------
    # Maintenance
    # ------------------------------------------------------------------
    def remove_analysis(self, analysis_id: str) -> bool:
        """Remove an analysis from the index (e.g. on delete/re-run)."""
        aid = str(analysis_id)
        removed = self._numpy_index.pop(aid, None) is not None
        if self._client is not None:
            # try all plausible collections; cheap to attempt
            try:
                cols = [c.name for c in self._client.get_collections().collections]
                for name in cols:
                    if name.startswith(COLLECTION_PREFIX):
                        self._client.delete(
                            collection_name=name,
                            points_selector=qmodels.PointIdsList(points=[aid]),
                        )
                removed = True
            except Exception as e:
                logger.warning(f"Qdrant delete failed: {e}")
        return removed

    def count(self) -> int:
        """Approximate number of indexed analyses (numpy backend only)."""
        if self._client is not None:
            total = 0
            try:
                cols = [c.name for c in self._client.get_collections().collections]
                for name in cols:
                    if name.startswith(COLLECTION_PREFIX):
                        info = self._client.count(
                            collection_name=name, exact=True).count
                        total += info
                return total
            except Exception:
                pass
        return len(self._numpy_index)


# Module-level singleton (mirrors the other agents' usage in views.py)
spectral_search_agent = SpectralSearchAgent()
