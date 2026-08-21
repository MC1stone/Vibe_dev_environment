import json
import os
import time

import paho.mqtt.client as mqtt
import uvicorn
from fastapi import FastAPI

BROKER = os.getenv("MQTT_BROKER", "localhost")
PORT = int(os.getenv("MQTT_PORT", "1883"))
SERVER_PORT = int(os.getenv("NAPARI_SERVER_PORT", "8002"))

app = FastAPI(title="Napari Server")
client = mqtt.Client()


@app.get("/health")
def health():
    return {"status": "ok", "service": "napari-server", "runtime": "headless"}


@app.get("/viewer/status")
def viewer_status():
    return {"viewer": "ready", "backend": "napari", "headless": True}


@app.post("/viewer/open")
def viewer_open(payload: dict):
    image_path = payload.get("image_path")
    return {
        "status": "queued",
        "image_path": image_path,
        "viewer": "napari",
        "message": "Napari viewer is prepared for integration into the existing Django/MCP workflow.",
    }


@app.post("/analysis/trigger")
def analysis_trigger(payload: dict):
    sample_id = payload.get("sample_id", "unknown")
    return {
        "status": "accepted",
        "sample_id": sample_id,
        "service": "napari-server",
        "note": "Raw acquisition handling is active; calibration and analysis are intentionally deferred.",
    }


def on_connect(client, userdata, flags, rc):
    print("[napari] Connected to MQTT broker")
    client.subscribe("spectral/#")


def on_message(client, userdata, msg):
    payload = msg.payload.decode("utf-8", errors="replace")
    print(f"[napari] topic={msg.topic} payload={payload}")


client.on_connect = on_connect
client.on_message = on_message

try:
    client.connect(BROKER, PORT, 60)
    client.loop_start()
except Exception as exc:
    print(f"[napari] MQTT init warning: {exc}")


if __name__ == "__main__":
    print("[napari] Napari server container is starting on port 8002")
    while True:
        client.publish("spectral/napari/status", json.dumps({"status": "running", "service": "napari-server"}))
        time.sleep(15)
