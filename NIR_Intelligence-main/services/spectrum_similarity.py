# NIR Intelligence Platform - Spectrum similarity engine (roadmap S5)
# Compares incoming spectra (unified spectral schema from S3/S4) against a
# reference set using nearest-neighbour search. Uses FAISS when installed and
# falls back to an exact numpy implementation otherwise; Qdrant is wired as
# the optional embedding-similarity backend (operational once S6 provides a
# running Qdrant instance).

import logging
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger("Service.SpectrumSimilarity")

try:
    import faiss  # optional backend, preferred when available

    FAISS_AVAILABLE = True
except ImportError:
    faiss = None
    FAISS_AVAILABLE = False


class SimilarityMatch:
    """One similarity hit against the reference set"""

    def __init__(self, reference_id: str, distance: float, similarity: float, reference_index: int):
        self.reference_id = reference_id
        self.distance = distance
        self.similarity = similarity
        self.reference_index = reference_index

    def to_dict(self) -> Dict[str, Any]:
        return {
            "reference_id": self.reference_id,
            "distance": float(self.distance),
            "similarity": float(self.similarity),
            "reference_index": self.reference_index,
        }


class SpectrumSimilarityEngine:
    """Nearest-neighbour spectrum comparison with FAISS/numpy backends.

    All inputs and outputs use the unified spectral data schema introduced in
    S3: {'data': DataFrame, 'wavelength_column': ..., 'intensity_column': ...}.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.wavelength_tolerance_nm = float(self.config.get("wavelength_tolerance_nm", 1.0))
        self.top_k = int(self.config.get("top_k", 5))
        self.metric = self.config.get("metric", "l2")
        self._faiss_index = None
        self._reference_ids: List[str] = []
        self._reference_vectors: Optional[np.ndarray] = None

    def _extract_intensity_vector(self, spectrum: Dict[str, Any]) -> Optional[np.ndarray]:
        """Extract the intensity vector from a unified spectral schema dict"""
        data = spectrum.get("data")
        if data is None:
            return None
        intensity_column = spectrum.get("intensity_column", "intensity")
        try:
            if hasattr(data, "columns"):  # pandas DataFrame
                if intensity_column not in data.columns:
                    logger.error("Intensity column '%s' not found", intensity_column)
                    return None
                values = data[intensity_column].to_numpy(dtype=np.float64)
            elif isinstance(data, dict):  # dict-of-arrays form
                if intensity_column not in data:
                    logger.error("Intensity column '%s' not found", intensity_column)
                    return None
                values = np.asarray(data[intensity_column], dtype=np.float64)
            else:
                return None
        except Exception as exc:
            logger.error("Failed to extract intensity vector: %s", exc)
            return None

        values = np.nan_to_num(values, nan=0.0, posinf=0.0, neginf=0.0)
        if values.size == 0:
            return None
        return values

    def _extract_wavelengths(self, spectrum: Dict[str, Any]) -> Optional[np.ndarray]:
        data = spectrum.get("data")
        wavelength_column = spectrum.get("wavelength_column", "wavelength")
        if data is None:
            return None
        if hasattr(data, "columns") and wavelength_column in data.columns:
            return data[wavelength_column].to_numpy(dtype=np.float64)
        if isinstance(data, dict) and wavelength_column in data:
            return np.asarray(data[wavelength_column], dtype=np.float64)
        return None

    def add_references(self, spectra: List[Dict[str, Any]], reference_ids: Optional[List[str]] = None) -> int:
        """Add reference spectra to the comparison index.

        reference_ids: one id per spectrum; when omitted, metadata.sample_id,
        metadata.session_id, source_file or the list position is used.
        """
        vectors: List[np.ndarray] = []
        ids: List[str] = []
        for position, spectrum in enumerate(spectra):
            vector = self._extract_intensity_vector(spectrum)
            if vector is None:
                continue
            if reference_ids is not None and position < len(reference_ids):
                reference_id = reference_ids[position]
            else:
                metadata = spectrum.get("metadata") or {}
                reference_id = (metadata.get("sample_id")
                                or metadata.get("session_id")
                                or spectrum.get("source_file")
                                or f"ref-{position}")
            vectors.append(vector)
            ids.append(str(reference_id))

        if not vectors:
            return 0

        dimension = len(vectors[0])
        for vector in vectors[1:]:
            if len(vector) != dimension:
                raise ValueError(
                    f"Reference spectra have inconsistent dimensions: {dimension} vs {len(vector)}"
                )

        self._reference_ids = self._reference_ids + ids
        stacked = np.vstack([v.astype(np.float32) for v in vectors])
        if self._reference_vectors is None:
            self._reference_vectors = stacked
        else:
            self._reference_vectors = np.vstack([self._reference_vectors, stacked])

        self._rebuild_faiss_index()
        return len(ids)

    def _rebuild_faiss_index(self) -> None:
        if not FAISS_AVAILABLE or self._reference_vectors is None:
            return
        vectors = np.ascontiguousarray(self._reference_vectors.astype(np.float32))
        dimension = vectors.shape[1]
        if self.metric == "cosine":
            index = faiss.IndexFlatIP(dimension)
            faiss.normalize_L2(vectors)
        else:
            index = faiss.IndexFlatL2(dimension)
        index.add(vectors)
        self._faiss_index = index

    def _faiss_search(self, query: np.ndarray, top_k: int) -> List[SimilarityMatch]:
        query = np.ascontiguousarray(query.astype(np.float32).reshape(1, -1))
        if self.metric == "cosine":
            faiss.normalize_L2(query)
        distances, indices = self._faiss_index.search(query, top_k)
        matches: List[SimilarityMatch] = []
        for distance, index in zip(distances[0], indices[0]):
            if index == -1:
                continue
            similarity = float(distance) if self.metric == "cosine" else 1.0 / (1.0 + float(distance))
            matches.append(SimilarityMatch(
                reference_id=self._reference_ids[index],
                distance=float(distance),
                similarity=similarity,
                reference_index=int(index),
            ))
        return matches

    def _numpy_search(self, query: np.ndarray, top_k: int) -> List[SimilarityMatch]:
        if self._reference_vectors is None or self._reference_vectors.shape[0] == 0:
            return []
        if self.metric == "cosine":
            q = query / (np.linalg.norm(query) or 1.0)
            refs = self._reference_vectors / (
                np.linalg.norm(self._reference_vectors, axis=1, keepdims=True) + 1e-12
            )
            sims = refs.dot(q)
            order = np.argsort(-sims)[:top_k]
            return [SimilarityMatch(self._reference_ids[i], float(-sims[i]), float(sims[i]), int(i))
                    for i in order]
        diffs = self._reference_vectors - query.astype(np.float32)
        squared = np.einsum("ij,ij->i", diffs, diffs)
        order = np.argsort(squared)[:top_k]
        return [SimilarityMatch(self._reference_ids[i], float(squared[i]),
                                1.0 / (1.0 + float(squared[i])), int(i))
                               for i in order]

    def find_similar(self, spectrum: Dict[str, Any], top_k: Optional[int] = None) -> List[SimilarityMatch]:
        """Find the most similar reference spectra for one query spectrum.

        Wavelength grids are compared when both sides provide them; a mismatch
        beyond wavelength_tolerance_nm is reported as an error instead of a
        silent wrong comparison.
        """
        top_k = top_k or self.top_k
        query = self._extract_intensity_vector(spectrum)
        if query is None:
            raise ValueError("Query spectrum has no usable intensity vector")

        if len(self._reference_ids) == 0:
            return []

        query_wavelengths = self._extract_wavelengths(spectrum)
        if query_wavelengths is not None and len(query_wavelengths) == len(query):
            if len(query_wavelengths) != len(self._reference_vectors[0]):
                raise ValueError(
                    f"Dimension mismatch: query has {len(query_wavelengths)} channels, "
                    f"reference set has {len(self._reference_vectors[0])}"
                )

        if FAISS_AVAILABLE and self._faiss_index is not None:
            matches = self._faiss_search(query, top_k)
        else:
            matches = self._numpy_search(query, top_k)
        return matches[:top_k]

    def status(self) -> Dict[str, Any]:
        return {
            "backend": "faiss" if FAISS_AVAILABLE else "numpy",
            "num_references": len(self._reference_ids),
            "dimension": int(self._reference_vectors.shape[1]) if self._reference_vectors is not None else None,
            "metric": self.metric,
            "top_k": self.top_k,
        }


class QdrantSimilarityService:
    """Optional Qdrant embedding-similarity backend (operational with S6).

    The platform targets Qdrant (6333) for embedding similarity; until the
    embedding pipeline exists (S6 chatbot) this service reports its state and
    defers the actual vector search to the QdrantAgent connection.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.host = self.config.get("host", "localhost")
        self.port = int(self.config.get("port", 6333))
        self.collection_name = self.config.get("collection_name", "nir_spectra")
        self._client = None

    def connect(self) -> Dict[str, Any]:
        try:
            from qdrant_client import QdrantClient

            client = QdrantClient(host=self.host, port=self.port, timeout=5)
            self._client = client
            return {"connected": True, "host": self.host, "port": self.port,
                    "collection": self.collection_name}
        except ImportError:
            logger.info("qdrant-client not installed; embedding similarity deferred")
            return {"connected": False, "reason": "qdrant_client not available",
                    "host": self.host, "port": self.port, "collection": self.collection_name}
        except Exception as exc:
            logger.warning("Qdrant connection failed: %s", exc)
            return {"connected": False, "reason": str(exc),
                    "host": self.host, "port": self.port, "collection": self.collection_name}

    def status(self) -> Dict[str, Any]:
        if self._client is None:
            return {"connected": False, "reason": "not connected"}
        return {"connected": True, "host": self.host, "port": self.port,
                "collection": self.collection_name}


def create_similarity_service(config: Optional[Dict[str, Any]] = None) -> SpectrumSimilarityEngine:
    """Factory used by the platform/agents to get the similarity engine"""
    return SpectrumSimilarityEngine(config=config)
