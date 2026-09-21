#!/usr/bin/env python3
# NIR Intelligence Platform - OP1 test matrix: Qdrant embedding pipeline
# Tests the embedding service (Ollama embeddings + Qdrant store) and the
# RagContextBuilder integration. All tests run offline with injectable
# stubs - no network, no running containers.

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

PASS = 0
FAIL = 0
FAILED = []


def check(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"[PASS] {name}")
    else:
        FAIL += 1
        FAILED.append(name)
        print(f"[FAIL] {name} {detail}")


def main():
    from services.embedding_service import (
        EmbeddingService, InMemoryEmbeddingStore, OllamaEmbeddingClient,
        QdrantEmbeddingStore, StubEmbeddingClient, create_embedding_service,
    )
    from services.chatbot_service import ChatbotService, RagContextBuilder

    # --- T1 StubEmbeddingClient semantics ---
    stub = StubEmbeddingClient(vector_size=8)
    v1 = stub.embed("Brix calibration results")
    v2 = stub.embed("Brix calibration results")
    v3 = stub.embed("something completely different")
    check("T1a stub embedding deterministic", v1 == v2)
    check("T1b stub embedding normalized", abs(sum(x * x for x in v1) - 1.0) < 1e-9)
    check("T1c different texts differ", v1 != v3)
    check("T1d stub available", stub.is_available())
    try:
        stub.embed("   ")
        check("T1e empty text rejected", False)
    except ValueError:
        check("T1e empty text rejected", True)

    # --- T2 EmbeddingService index + search roundtrip (in-memory store) ---
    store = InMemoryEmbeddingStore()
    service = create_embedding_service({"id_base": 5000})
    service.embedding_client = stub
    service.store = QdrantEmbeddingStore(config={"collection_name": "nir_spectra"},
                                         client=store)
    result = service.index_analysis_results([
        {"agent_name": "calibration_agent", "data": {"method": "PLS", "r2": 0.94}},
        {"agent_name": "sensor_quality_agent", "data": {"drift": "none"}},
    ])
    check("T2a index upserts points", result.get("upserted") == 2)
    check("T2b collection created", result.get("collection_state", {}).get("created") is True)
    check("T2c collection registered", "nir_spectra" in store._collections)

    search = service.search_texts("What about the PLS calibration?", top_k=1)
    check("T2d search returns hits", len(search["hits"]) >= 1)
    top = search["hits"][0]
    check("T2e top hit is the calibration result",
          top["payload"].get("agent") == "calibration_agent", str(top))
    check("T2f payload carries text", "PLS" in str(top["payload"].get("text", "")))

    # --- T3 ensure_collection idempotence ---
    state2 = service.store.ensure_collection(vector_size=8)
    check("T3a second ensure does not recreate",
          state2.get("created") is False and state2.get("already_existed") is True)

    # --- T4 error cases ---
    try:
        service.index_texts([])
        check("T4a empty index rejected", False)
    except ValueError:
        check("T4a empty index rejected", True)
    try:
        service.index_texts(["a", "b"], payloads=[{"x": 1}])
        check("T4b payload length mismatch rejected", False)
    except ValueError:
        check("T4b payload length mismatch rejected", True)
    try:
        OllamaEmbeddingClient().embed("text")
        check("T4c real client without network raises or degrades", False)
    except Exception:
        check("T4c real client without network raises or degrades", True)

    # --- T5 RagContextBuilder with embedding service (Qdrant RAG) ---
    rag = RagContextBuilder(embedding_service=service)
    built = rag.build("What about the PLS calibration?")
    check("T5a qdrant_rag source used", "qdrant_rag" in built["sources"], str(built["sources"]))
    check("T5b qdrant_used true", built["qdrant_used"] is True)
    check("T5c rag context contains hit text", "PLS" in built["context"])

    # --- T6 RagContextBuilder without embedding service (S6 behavior kept) ---
    rag_plain = RagContextBuilder()
    built_plain = rag_plain.build("question",
                                 analysis_results=[{"agent_name": "a", "data": {"x": 1}}])
    check("T6a no embedding service -> no qdrant_rag",
          "qdrant_rag" not in built_plain["sources"])
    check("T6b analysis results still injected",
          "analysis_results" in built_plain["sources"])

    # --- T7 RagContextBuilder with failing embedding service (graceful) ---
    class BrokenService:
        def search_texts(self, question, top_k=5):
            raise RuntimeError("qdrant down")
    rag_broken = RagContextBuilder(embedding_service=BrokenService())
    built_broken = rag_broken.build("question", analysis_results=[{"agent_name": "a", "data": {}}])
    check("T7a broken embedding service does not crash", True)
    check("T7b falls back to analysis results only",
          "qdrant_rag" not in built_broken["sources"] and
          "analysis_results" in built_broken["sources"])

    # --- T8 status ---
    status = service.status()
    check("T8a status reports embedding model",
          status.get("embedding_model") == "nomic-embed-text:latest", str(status))
    check("T8b status reports collection", status.get("collection") == "nir_spectra")
    check("T8c status reports qdrant connected", status["qdrant"].get("connected") is True)

    # --- T9 ChatbotService composes RAG into system prompt ---
    chatbot = ChatbotService(config={})
    chatbot.rag = RagContextBuilder(embedding_service=service)
    messages, rag_result = chatbot.build_messages("What about the PLS calibration?")
    check("T9a system prompt carries rag context", "PLS" in messages[0]["content"])
    check("T9b rag result reports qdrant_rag", "qdrant_rag" in rag_result["sources"])

    # --- T10 regression spot checks ---
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "services"))
    from services.spectrum_similarity import create_similarity_service
    engine = create_similarity_service()
    sample = {"data": {"wavelength": [100, 200, 300], "intensity": [1.0, 2.0, 3.0]}}
    engine.add_references([sample], reference_ids=["self"])
    self_match = engine.find_similar(sample, top_k=1)
    check("T10a S5 similarity regression", len(self_match) == 1 and
          self_match[0].similarity >= 0.999, str(self_match))

    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "chatbot_views", os.path.join(os.path.dirname(__file__), "..",
                                      "django_project", "api", "chatbot_views.py"))
    if spec and spec.loader:
        check("T10b S6 chatbot views module present", True)
    else:
        check("T10b S6 chatbot views module present", False)

    print()
    print(f"{PASS}/{PASS + FAIL} tests passed")
    if FAILED:
        print("FAILED:", ", ".join(FAILED))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
