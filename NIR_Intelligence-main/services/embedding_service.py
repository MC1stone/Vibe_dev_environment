# NIR Intelligence Platform - Embedding service (target-environment OP1)
# Text-to-vector embeddings via Ollama (/api/embeddings) plus Qdrant
# collection management, upsert and top-k search. Operationalizes the
# Qdrant RAG pipeline promised in S5/S6: analysis results and Quarto
# documentation chunks are embedded once and retrieved as chat context.
#
# Design constraints:
# - No new hard dependencies: requests + qdrant-client are already
#   declared in requirements.txt; both are optional imports with
#   graceful degradation.
# - Clients are injectable so tests run without network.
# - Raw spectra are never embedded - embeddings are computed over text
#   (analysis result summaries, documentation chunks) only.

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("Service.Embedding")

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    requests = None
    REQUESTS_AVAILABLE = False

OLLAMA_DEFAULT_URL = "http://ollama:11434"
DEFAULT_EMBEDDING_MODEL = "nomic-embed-text:latest"
DEFAULT_COLLECTION = "nir_spectra"
DEFAULT_VECTOR_SIZE_HINT = 768
DEFAULT_TOP_K = 5


class OllamaEmbeddingClient:
    """Thin HTTP client for the Ollama embedding API (/api/embeddings)."""

    def __init__(self, base_url: str = OLLAMA_DEFAULT_URL,
                 model: str = DEFAULT_EMBEDDING_MODEL, timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def embed(self, text: str) -> List[float]:
        if not REQUESTS_AVAILABLE:
            raise RuntimeError("requests package not available")
        if not text or not text.strip():
            raise ValueError("cannot embed empty text")
        response = requests.post(
            f"{self.base_url}/api/embeddings",
            json={"model": self.model, "prompt": text},
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        embedding = payload.get("embedding")
        if not embedding or not isinstance(embedding, list):
            raise ValueError(f"no embedding in Ollama response for model {self.model}")
        return embedding

    def is_available(self) -> bool:
        if not REQUESTS_AVAILABLE:
            return False
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception:
            return False


class StubEmbeddingClient:
    """Deterministic stub for tests - hashes the text into a fixed-size vector."""

    def __init__(self, vector_size: int = 8):
        self.vector_size = vector_size

    def embed(self, text: str) -> List[float]:
        if not text or not text.strip():
            raise ValueError("cannot embed empty text")
        vector = [0.0] * self.vector_size
        for index, char in enumerate(text):
            vector[index % self.vector_size] += float(ord(char) % 97) / 97.0
        norm = sum(v * v for v in vector) ** 0.5 or 1.0
        return [v / norm for v in vector]

    def is_available(self) -> bool:
        return True


class QdrantEmbeddingStore:
    """Qdrant collection management + upsert + top-k search over embeddings."""

    def __init__(self, config: Optional[Dict[str, Any]] = None,
                 client: Any = None):
        self.config = config or {}
        self.host = self.config.get("host", "localhost")
        self.port = int(self.config.get("port", 6333))
        self.collection_name = self.config.get("collection_name", DEFAULT_COLLECTION)
        self.vector_size = int(self.config.get("vector_size", DEFAULT_VECTOR_SIZE_HINT))
        self._client = client
        self._owns_client = False

    def _ensure_client(self):
        if self._client is None:
            from qdrant_client import QdrantClient
            self._client = QdrantClient(host=self.host, port=self.port, timeout=5)
            self._owns_client = True
        return self._client

    def connect(self) -> Dict[str, Any]:
        try:
            self._ensure_client()
            self._client.get_collections()
            return {"connected": True, "host": self.host, "port": self.port,
                    "collection": self.collection_name}
        except ImportError:
            return {"connected": False, "reason": "qdrant_client not available",
                    "host": self.host, "port": self.port, "collection": self.collection_name}
        except Exception as exc:
            logger.warning("Qdrant connection failed: %s", exc)
            return {"connected": False, "reason": str(exc),
                    "host": self.host, "port": self.port, "collection": self.collection_name}

    def ensure_collection(self, vector_size: Optional[int] = None) -> Dict[str, Any]:
        client = self._ensure_client()
        size = int(vector_size or self.vector_size)
        if not self.collection_exists():
            vectors_config = size
            if not isinstance(client, InMemoryEmbeddingStore):
                from qdrant_client.models import Distance, VectorParams
                vectors_config = VectorParams(size=size, distance=Distance.COSINE)
            client.create_collection(
                collection_name=self.collection_name,
                vectors_config=vectors_config,
            )
            return {"created": True, "collection": self.collection_name, "vector_size": size}
        return {"created": False, "collection": self.collection_name,
                "vector_size": size, "already_existed": True}

    def collection_exists(self) -> bool:
        client = self._ensure_client()
        try:
            collections = client.get_collections()
            names = [getattr(c, "name", None) for c in collections.collections]
            return self.collection_name in names
        except Exception as exc:
            logger.warning("collection_exists check failed: %s", exc)
            return False

    def upsert(self, points: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not points:
            raise ValueError("no points to upsert")
        client = self._ensure_client()
        if isinstance(client, InMemoryEmbeddingStore):
            structs = points
        else:
            from qdrant_client.models import PointStruct
            structs = [
                PointStruct(
                    id=p["id"],
                    vector=p["vector"],
                    payload=p.get("payload", {}),
                )
                for p in points
            ]
        client.upsert(collection_name=self.collection_name, points=structs)
        return {"upserted": len(structs), "collection": self.collection_name}

    def search(self, vector: List[float], top_k: int = DEFAULT_TOP_K) -> List[Dict[str, Any]]:
        client = self._ensure_client()
        if not self.collection_exists():
            return []
        results = client.query_points(
            collection_name=self.collection_name,
            query=vector,
            limit=int(top_k),
            with_payload=True,
        )
        hits = []
        for scored in results.points:
            hits.append({
                "id": getattr(scored, "id", None),
                "score": getattr(scored, "score", None),
                "payload": getattr(scored, "payload", {}) or {},
            })
        return hits


class EmbeddingService:
    """End-to-end pipeline: text -> vector -> Qdrant upsert / top-k search."""

    def __init__(self, config: Optional[Dict[str, Any]] = None,
                 embedding_client: Any = None, store: Any = None):
        self.config = config or {}
        self.ollama_url = self.config.get("ollama_url", OLLAMA_DEFAULT_URL)
        self.model = self.config.get("embedding_model", DEFAULT_EMBEDDING_MODEL)
        self.collection_name = self.config.get("collection_name", DEFAULT_COLLECTION)
        self.embedding_client = embedding_client or OllamaEmbeddingClient(
            base_url=self.ollama_url, model=self.model)
        self.store = store or QdrantEmbeddingStore(config={
            "host": self.config.get("qdrant_host", "localhost"),
            "port": self.config.get("qdrant_port", 6333),
            "collection_name": self.collection_name,
        })

    def _sequence_id(self, index: int) -> int:
        return int(self.config.get("id_base", 1000)) + index

    def index_texts(self, texts: List[str], payloads: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        if not texts:
            raise ValueError("no texts to index")
        if payloads is not None and len(payloads) != len(texts):
            raise ValueError("payloads length must match texts length")
        vectors = [self.embedding_client.embed(text) for text in texts]
        state = self.store.ensure_collection(vector_size=len(vectors[0]))
        points = []
        for i, vector in enumerate(vectors):
            points.append({
                "id": self._sequence_id(i),
                "vector": vector,
                "payload": (payloads[i] if payloads else {"text": texts[i], "index": i}),
            })
        result = self.store.upsert(points)
        result["collection_state"] = state
        return result

    def index_analysis_results(self, analysis_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        texts, payloads = [], []
        for i, result in enumerate(analysis_results):
            agent = result.get("agent_name", f"result-{i}")
            data = result.get("data", {})
            texts.append(f"[{agent}] {data}")
            payloads.append({"source": "analysis_results", "agent": agent,
                             "text": f"[{agent}] {data}", "index": i})
        return self.index_texts(texts, payloads)

    def search_texts(self, question: str, top_k: int = DEFAULT_TOP_K) -> Dict[str, Any]:
        vector = self.embedding_client.embed(question)
        hits = self.store.search(vector, top_k=top_k)
        return {"question": question, "hits": hits, "top_k": top_k}

    def status(self) -> Dict[str, Any]:
        embedding_available = False
        try:
            embedding_available = self.embedding_client.is_available()
        except Exception:
            embedding_available = False
        store_state = self.store.connect()
        return {
            "service": "embedding",
            "embedding_model": self.model,
            "embedding_available": embedding_available,
            "qdrant": store_state,
            "collection": self.collection_name,
        }


class InMemoryEmbeddingStore:
    """Local stand-in for Qdrant used in tests and offline demos."""

    def __init__(self, vector_size: int = DEFAULT_VECTOR_SIZE_HINT):
        self.vector_size = vector_size
        self._points: Dict[int, Dict[str, Any]] = {}
        self._collections: List[str] = []

    def get_collections(self):
        class _Collections:
            def __init__(self, names):
                self.collections = [type("C", (), {"name": n})() for n in names]
        return _Collections(list(self._collections))

    def create_collection(self, collection_name: str, vectors_config: Any = None) -> None:
        self._collections.append(collection_name)

    def upsert(self, collection_name: str, points: List[Any]) -> None:
        for point in points:
            if isinstance(point, dict):
                self._points[point["id"]] = {"vector": point["vector"],
                                             "payload": point.get("payload", {})}
            else:
                self._points[point.id] = {"vector": point.vector, "payload": point.payload}

    def query_points(self, collection_name: str, query: List[float],
                     limit: int = DEFAULT_TOP_K, with_payload: bool = True) -> Any:
        import math

        class _Scored:
            def __init__(self, pid, vector, payload, score):
                self.id = pid
                self.score = score
                self.payload = payload
                self.vector = vector

        def cosine(a: List[float], b: List[float]) -> float:
            dot = sum(x * y for x, y in zip(a, b))
            na = math.sqrt(sum(x * x for x in a)) or 1.0
            nb = math.sqrt(sum(x * x for x in b)) or 1.0
            return dot / (na * nb)

        scored = [
            _Scored(pid, entry["vector"], entry["payload"], cosine(query, entry["vector"]))
            for pid, entry in self._points.items()
        ]
        scored.sort(key=lambda s: s.score, reverse=True)

        class _Result:
            def __init__(self, points):
                self.points = points

        return _Result(scored[:limit])


def create_embedding_service(config: Optional[Dict[str, Any]] = None) -> EmbeddingService:
    """Factory used by the platform/agents to get the embedding pipeline."""
    return EmbeddingService(config=config)
