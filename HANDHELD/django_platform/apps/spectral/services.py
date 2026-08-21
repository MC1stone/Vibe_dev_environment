import json
import os

import paho.mqtt.client as mqtt


def publish_raw_capture(topic: str, payload: dict) -> bool:
    broker = os.getenv("MQTT_BROKER", "mqtt")
    port = int(os.getenv("MQTT_PORT", "1883"))
    client = mqtt.Client()
    try:
        client.connect(broker, port, 10)
        client.publish(topic, json.dumps(payload), qos=1)
        client.disconnect()
        return True
    except Exception:
        return False
