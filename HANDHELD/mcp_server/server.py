import json
import os

import paho.mqtt.client as mqtt
from fastapi import FastAPI

app = FastAPI(title="Spectral MCP Server")

BROKER = os.getenv("MQTT_BROKER", "localhost")
PORT = int(os.getenv("MQTT_PORT", "1883"))

client = mqtt.Client()


def on_connect(client, userdata, flags, rc):
    print("[mcp] Connected to MQTT broker")
    client.subscribe("spectral/#")


def on_message(client, userdata, msg):
    payload = msg.payload.decode("utf-8", errors="replace")
    print(f"[mcp] {msg.topic}: {payload}")


client.on_connect = on_connect
client.on_message = on_message

try:
    client.connect(BROKER, PORT, 60)
    client.loop_start()
except Exception as exc:
    print(f"[mcp] MQTT init warning: {exc}")


@app.get("/health")
def health():
    return {"status": "ok", "service": "mcp-server"}


@app.post("/tool/run")
def run_tool(payload: dict):
    tool_name = payload.get("tool")
    args = payload.get("args", {})
    if client.is_connected():
        client.publish("spectral/tool/run", json.dumps({"tool": tool_name, "args": args}))
    return {"accepted": True, "tool": tool_name, "args": args}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
