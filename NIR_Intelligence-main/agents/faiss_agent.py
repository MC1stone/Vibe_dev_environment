# NIR Intelligence Platform - FAISS Agent
# Handles similarity search operations via the SpectrumSimilarityEngine (S5):
# FAISS backend when installed, exact numpy fallback otherwise.

from typing import Any, Dict

from .base_agent import AgentOutput, AgentStatus, BaseAgent, ErrorSeverity


class FaissAgent(BaseAgent):
    """Agent for managing FAISS similarity search"""

    def __init__(self, **kwargs):
        super().__init__(name="FaissAgent", version="1.1.0", **kwargs)
        self.dependencies = ["faiss-cpu", "numpy"]
        self.index_type = kwargs.get("index_type", "IVF100,Flat")
        self.metric_type = kwargs.get("metric_type", "L2")
        self.nprobe = kwargs.get("nprobe", 10)

    def execute(self, context: Dict[str, Any]) -> AgentOutput:
        """Execute FAISS similarity operations.

        context keys:
        - reference_spectra: list of unified spectral schema dicts
        - query_spectrum: one unified spectral schema dict
        - reference_ids: optional list of reference ids
        - top_k: optional number of matches (default 5)
        """
        try:
            self.status = AgentStatus.PROCESSING
            self.logger.info("Starting FAISS agent execution")

            from services.spectrum_similarity import SpectrumSimilarityEngine

            engine = SpectrumSimilarityEngine(config={
                "metric": "cosine" if str(self.metric_type).upper() == "COSINE" else "l2",
                "top_k": int(context.get("top_k", 5)),
            })

            references = context.get("reference_spectra") or []
            query = context.get("query_spectrum")

            if references:
                added = engine.add_references(references, reference_ids=context.get("reference_ids"))
                self.logger.info(f"Added {added} reference spectra to the index")

            faiss_results = {"engine_status": engine.status()}

            if query is not None:
                matches = engine.find_similar(query)
                faiss_results["matches"] = [m.to_dict() for m in matches]
                faiss_results["num_matches"] = len(matches)

            self.status = AgentStatus.COMPLETED
            return self._create_success_output(faiss_results)

        except Exception as e:
            return self._handle_error(e)
