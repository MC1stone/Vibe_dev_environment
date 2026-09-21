# NIR Intelligence Platform - Chatbot API views (roadmap S6, MO 10)
# Django REST endpoints for discussing analysis results with the
# Ollama/Mistral chatbot (services/chatbot_service.py).

import logging

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

logger = logging.getLogger("API.Chatbot")


def _get_chatbot_service():
    from services.chatbot_service import create_chatbot_service

    return create_chatbot_service(config={
        "ollama_url": getattr(settings_local(), "OLLAMA_URL", "http://ollama:11434"),
        "model": getattr(settings_local(), "OLLAMA_MODEL", "mistral:latest"),
        "qdrant_host": getattr(settings_local(), "QDRANT_HOST", "qdrant"),
        "qdrant_port": getattr(settings_local(), "QDRANT_PORT", 6333),
    })


def settings_local():
    from django.conf import settings

    return settings


@api_view(["POST"])
@permission_classes([AllowAny])
def chatbot_message(request):
    """POST /api/chatbot/message/

    Body:
    {
      "question": "...",
      "analysis_results": [...],   # optional agent outputs (AgentOutput.data style)
      "documents": [{"source": "...", "text": "..."}],  # optional RAG documents
      "history": [{"role": "user"|"assistant", "content": "..."}]  # optional turns
    }
    """
    question = request.data.get("question")
    if not question or not str(question).strip():
        return Response({"error": "question is required"},
                        status=status.HTTP_400_BAD_REQUEST)

    service = _get_chatbot_service()
    result = service.chat(
        question=str(question),
        analysis_results=request.data.get("analysis_results"),
        documents=request.data.get("documents"),
        history=request.data.get("history"),
    )

    if result.get("degraded"):
        return Response({
            "answer": None,
            "error": result.get("error"),
            "degraded": True,
            "rag_sources": result.get("rag_sources", []),
        }, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    return Response({
        "answer": result.get("answer"),
        "model": result.get("model"),
        "degraded": False,
        "rag_sources": result.get("rag_sources", []),
    })


@api_view(["GET"])
@permission_classes([AllowAny])
def chatbot_status(request):
    """GET /api/chatbot/status/ - chatbot/Ollama availability"""
    service = _get_chatbot_service()
    return Response(service.status())
