# NIR Intelligence Platform - Result chatbot service (roadmap S6, MO 10)
# Chat interface for discussing analysis results, backed by Ollama
# (Mistral:latest) with optional Qdrant RAG context over analysis results
# and documentation. No chat history persistence, no streaming - the Django
# frontend passes the conversation turns explicitly with each request.

import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("Service.Chatbot")

try:
    import requests

    REQUESTS_AVAILABLE = True
except ImportError:
    requests = None
    REQUESTS_AVAILABLE = False

OLLAMA_DEFAULT_URL = "http://ollama:11434"
DEFAULT_MODEL = "mistral:latest"
RAG_COLLECTION = "nir_spectra"

SYSTEM_PROMPT = (
    "You are the result discussion assistant of the NIR Intelligence Platform "
    "(NIR-IP). You answer questions about near-infrared spectroscopy analysis "
    "results, calibrations, sensor quality and similarity findings. Use the "
    "provided context when available; state clearly when the context does not "
    "contain the answer. Keep answers precise and factual."
)


class ChatMessage:
    """One conversation turn"""

    def __init__(self, role: str, content: str):
        self.role = role
        self.content = content

    def to_dict(self) -> Dict[str, str]:
        return {"role": self.role, "content": self.content}


class OllamaChatClient:
    """Thin HTTP client for the Ollama chat API (/api/chat)"""

    def __init__(self, base_url: str = OLLAMA_DEFAULT_URL, model: str = DEFAULT_MODEL,
                 timeout: int = 120):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def chat(self, messages: List[Dict[str, str]], options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if not REQUESTS_AVAILABLE:
            raise RuntimeError("requests package not available")
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
        }
        if options:
            payload["options"] = options
        response = requests.post(
            f"{self.base_url}/api/chat",
            json=payload,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def is_available(self) -> bool:
        if not REQUESTS_AVAILABLE:
            return False
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception:
            return False


class RagContextBuilder:
    """Builds the RAG context injected into the chat prompt.

    Retrieves related documents from Qdrant when the embedding backend is
    reachable; falls back to the locally provided analysis summary otherwise.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None,
                 embedding_service: Any = None):
        self.config = config or {}
        self.collection_name = self.config.get("collection_name", RAG_COLLECTION)
        self._qdrant_state: Optional[Dict[str, Any]] = None
        self.embedding_service = embedding_service
        self.rag_top_k = int(self.config.get("rag_top_k", 5))

    def build(self, question: str, analysis_results: Optional[List[Dict[str, Any]]] = None,
              documents: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        context_parts: List[str] = []
        sources: List[str] = []
        used_qdrant = False

        if analysis_results:
            summary_lines = []
            for i, result in enumerate(analysis_results):
                agent = result.get("agent_name", f"result-{i}")
                data = result.get("data", {})
                summary_lines.append(f"[{agent}] {json.dumps(data, default=str)[:2000]}")
            context_parts.append("Analysis results:\n" + "\n".join(summary_lines))
            sources.append("analysis_results")

        if documents:
            doc_lines = [f"[doc:{d.get('source', 'unknown')}] {d.get('text', '')[:2000]}"
                         for d in documents]
            context_parts.append("Documentation:\n" + "\n".join(doc_lines))
            sources.append("documents")

        if self.embedding_service is not None:
            try:
                search_result = self.embedding_service.search_texts(
                    question, top_k=self.rag_top_k)
                rag_texts = []
                for hit in search_result.get("hits", []):
                    payload = hit.get("payload", {}) or {}
                    text = payload.get("text", "")
                    if text:
                        rag_texts.append(
                            f"[rag:score={hit.get('score', 0):.3f}] {text[:2000]}")
                if rag_texts:
                    context_parts.append("Qdrant RAG results:\n" + "\n".join(rag_texts))
                    sources.append("qdrant_rag")
                    used_qdrant = True
            except Exception as exc:
                logger.warning("Qdrant RAG retrieval failed, continuing without: %s", exc)

        return {
            "context": "\n\n".join(context_parts),
            "sources": sources,
            "qdrant_used": used_qdrant,
            "qdrant_state": self._qdrant_state,
        }

    def connect_qdrant(self, host: str = "localhost", port: int = 6333) -> Dict[str, Any]:
        from services.spectrum_similarity import QdrantSimilarityService

        service = QdrantSimilarityService(config={
            "host": host, "port": port, "collection_name": self.collection_name})
        state = service.connect()
        self._qdrant_state = state
        return state


class ChatbotService:
    """Result discussion chatbot: Ollama chat with RAG context (S6)"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.ollama_url = self.config.get("ollama_url", OLLAMA_DEFAULT_URL)
        self.model = self.config.get("model", DEFAULT_MODEL)
        self.qdrant_host = self.config.get("qdrant_host", "localhost")
        self.qdrant_port = int(self.config.get("qdrant_port", 6333))
        self.client = OllamaChatClient(base_url=self.ollama_url, model=self.model)
        self.rag = RagContextBuilder(config=self.config)

    def build_messages(self, question: str,
                       analysis_results: Optional[List[Dict[str, Any]]] = None,
                       documents: Optional[List[Dict[str, str]]] = None,
                       history: Optional[List[Dict[str, str]]] = None) -> List[Dict[str, str]]:
        """Compose the message list sent to Ollama (system + RAG + history + question)"""
        rag_result = self.rag.build(question, analysis_results=analysis_results,
                                    documents=documents)
        system_content = SYSTEM_PROMPT
        if rag_result["context"]:
            system_content += "\n\nContext:\n" + rag_result["context"]

        messages: List[Dict[str, str]] = [{"role": "system", "content": system_content}]
        for turn in history or []:
            messages.append({"role": turn.get("role", "user"),
                             "content": turn.get("content", "")})
        messages.append({"role": "user", "content": question})
        return messages, rag_result

    def chat(self, question: str,
             analysis_results: Optional[List[Dict[str, Any]]] = None,
             documents: Optional[List[Dict[str, str]]] = None,
             history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        """Ask the chatbot; returns answer plus metadata about the RAG context."""
        messages, rag_result = self.build_messages(question, analysis_results,
                                                   documents, history)
        try:
            raw = self.client.chat(messages)
            answer = raw.get("message", {}).get("content", "")
            return {
                "answer": answer,
                "model": raw.get("model", self.model),
                "rag_sources": rag_result["sources"],
                "qdrant_used": rag_result["qdrant_used"],
                "degraded": False,
                "error": None,
            }
        except Exception as exc:
            logger.error("Ollama chat failed: %s", exc)
            return {
                "answer": None,
                "model": self.model,
                "rag_sources": rag_result["sources"],
                "qdrant_used": rag_result["qdrant_used"],
                "degraded": True,
                "error": str(exc),
            }

    def status(self) -> Dict[str, Any]:
        return {
            "service": "chatbot",
            "ollama_url": self.ollama_url,
            "model": self.model,
            "ollama_available": self.client.is_available(),
        }


def create_chatbot_service(config: Optional[Dict[str, Any]] = None) -> ChatbotService:
    """Factory used by the Django layer to get the chatbot service"""
    return ChatbotService(config=config)
