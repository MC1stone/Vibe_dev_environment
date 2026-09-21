# NIR Intelligence Platform - Qdrant Agent
# Handles vector database operations (replaces the out-of-scope Weaviate).
# Embedding similarity is wired via QdrantSimilarityService (S5); the
# embedding pipeline itself follows with the S6 chatbot.

from typing import Any, Dict

from .base_agent import AgentOutput, AgentStatus, BaseAgent, ErrorSeverity


class QdrantAgent(BaseAgent):
    """Agent for managing the Qdrant vector database"""

    def __init__(self, **kwargs):
        super().__init__(name="QdrantAgent", version="1.1.0", **kwargs)
        self.dependencies = ["qdrant-client", "numpy"]
        self.host = kwargs.get("host", "localhost")
        self.port = kwargs.get("port", 6333)
        self.collection_name = kwargs.get("collection_name", "nir_spectra")

    def execute(self, context: Dict[str, Any]) -> AgentOutput:
        """Execute Qdrant operations.

        context keys:
        - host / port / collection_name: connection overrides
        - action: 'status' (default) - reports the Qdrant connection state
        """
        try:
            self.status = AgentStatus.PROCESSING
            self.logger.info("Starting Qdrant agent execution")

            from services.spectrum_similarity import QdrantSimilarityService

            service = QdrantSimilarityService(config={
                "host": context.get("host", self.host),
                "port": context.get("port", self.port),
                "collection_name": context.get("collection_name", self.collection_name),
            })

            self.logger.info(f"Qdrant connection: http://{service.host}:{service.port}")
            state = service.connect()

            qdrant_results = {
                "connection_established": state.get("connected", False),
                "host": service.host,
                "port": service.port,
                "collection": service.collection_name,
                "detail": state.get("reason", "connected"),
                "embedding_pipeline": "deferred to S6",
            }

            self.status = AgentStatus.COMPLETED
            return self._create_success_output(qdrant_results)
        except Exception as e:
            return self._handle_error(e)
