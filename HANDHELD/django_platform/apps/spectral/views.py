import json
from datetime import datetime

from datetime import datetime

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf
from django.views.decorators.http import require_http_methods

from .models import AcquisitionSession, NapariResult, RawFrame, SensorProfile
from .services import publish_raw_capture


@csrf
@require_http_methods(["POST"])
def create_sensor_profile(request):
    try:
        payload = json.loads(request.body.decode("utf-8")) if request.body else request.POST
    except ValueError:
        payload = request.POST

    name = payload.get("name")
    interface_type = payload.get("interface_type", "mock")
    device_path = payload.get("device_path", "")
    serial_number = payload.get("serial_number", "")
    connection_settings = payload.get("connection_settings", {})
    metadata = payload.get("metadata", {})

    if not name:
        return JsonResponse({"error": "name is required"}, status=400)

    sensor = SensorProfile.objects.create(
        name=name,
        interface_type=interface_type,
        device_path=device_path,
        serial_number=serial_number,
        connection_settings=connection_settings,
        metadata=metadata,
    )

    return JsonResponse({
        "id": sensor.id,
        "name": sensor.name,
        "interface_type": sensor.interface_type,
        "device_path": sensor.device_path,
        "metadata": sensor.metadata,
    }, status=201)


@csrf
@require_http_methods(["POST"])
def create_acquisition_session(request):
    try:
        payload = json.loads(request.body.decode("utf-8")) if request.body else request.POST
    except ValueError:
        payload = request.POST

    sensor_id = payload.get("sensor_id")
    name = payload.get("name", "acquisition-session")
    metadata = payload.get("metadata", {})
    notes = payload.get("notes", "")

    if not sensor_id:
        return JsonResponse({"error": "sensor_id is required"}, status=400)

    sensor = SensorProfile.objects.get(id=sensor_id)
    session = AcquisitionSession.objects.create(
        sensor=sensor,
        name=name,
        status="recording",
        metadata=metadata,
        notes=notes,
    )

    publish_raw_capture("spectral/session/create", {
        "session_id": session.id,
        "sensor_id": sensor.id,
        "name": session.name,
        "status": session.status,
        "metadata": session.metadata,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    })

    return JsonResponse({
        "id": session.id,
        "name": session.name,
        "status": session.status,
        "sensor_id": sensor.id,
    }, status=201)


@csrf
@require_http_methods(["POST"])
def store_raw_frame(request):
    try:
        payload = json.loads(request.body.decode("utf-8")) if request.body else request.POST
    except ValueError:
        payload = request.POST

    session_id = payload.get("session_id")
    sample_id = payload.get("sample_id", "")
    exposure_ms = payload.get("exposure_ms", 0.0)
    file_path = payload.get("file_path", "")
    raw_payload = payload.get("raw_payload", {})
    metadata = payload.get("metadata", {})

    if not session_id:
        return JsonResponse({"error": "session_id is required"}, status=400)

    session = AcquisitionSession.objects.get(id=session_id)
    frame = RawFrame.objects.create(
        session=session,
        sample_id=sample_id,
        exposure_ms=float(exposure_ms),
        file_path=file_path,
        raw_payload=raw_payload,
        metadata=metadata,
    )

    publish_raw_capture("spectral/raw/capture", {
        "session_id": session.id,
        "frame_id": frame.id,
        "sample_id": sample_id,
        "exposure_ms": float(exposure_ms),
        "file_path": file_path,
        "metadata": metadata,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    })

    return JsonResponse({
        "id": frame.id,
        "session_id": session.id,
        "sample_id": sample_id,
        "timestamp": frame.timestamp.isoformat(),
        "status": "stored",
    }, status=201)


@csrf
@require_http_methods(["POST", "GET"])
def capture_napari_result(request):
    if request.method == "GET":
        results = NapariResult.objects.select_related("session").order_by("-created_at")
        payload = [{
            "id": item.id,
            "title": item.title,
            "status": item.status,
            "summary": item.summary,
            "image_url": item.image_url,
            "metrics": item.metrics,
            "created_at": item.created_at.isoformat(),
            "session_id": item.session_id,
        } for item in results]
        return JsonResponse({"results": payload})

    try:
        payload = json.loads(request.body.decode("utf-8")) if request.body else request.POST
    except ValueError:
        payload = request.POST

    session_id = payload.get("session_id")
    title = payload.get("title", "Napari Result")
    summary = payload.get("summary", "")
    image_url = payload.get("image_url", "")
    metrics = payload.get("metrics", {})
    status = payload.get("status", "ready")

    if not session_id:
        return JsonResponse({"error": "session_id is required"}, status=400)

    session = AcquisitionSession.objects.get(id=session_id)
    result = NapariResult.objects.create(
        session=session,
        title=title,
        summary=summary,
        image_url=image_url,
        metrics=metrics,
        status=status,
        published_at=datetime.utcnow(),
    )

    publish_raw_capture("spectral/napari/result", {
        "result_id": result.id,
        "session_id": session.id,
        "title": title,
        "status": status,
        "summary": summary,
        "metrics": metrics,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    })

    return JsonResponse({
        "id": result.id,
        "title": result.title,
        "status": result.status,
        "summary": result.summary,
        "url": result.image_url,
    }, status=201)


def napari_results_dashboard(request):
    results = NapariResult.objects.select_related("session").order_by("-created_at")
    context = {"results": results}
    return render(request, "spectral/results.html", context)


def napari_result_detail(request, result_id):
    result = NapariResult.objects.select_related("session").get(id=result_id)
    return render(request, "spectral/result_detail.html", {"result": result})


def demo_spectrum_view(request):
    return render(request, "spectral/demo_spectrum.html")
