#!/usr/bin/env python3

import paho.mqtt.client as mqtt
import json
import base64

topic="application/0dc3fcd5-269f-4835-9fcb-ea6ab18efe10/device/8cf957200000f639/event/up"
# topic="application/<chirpstack-application-id>/device/<device-id>/event/up"

def on_connect(client, userdata, flags, rc):
    print("Connected with result code", rc)
    client.subscribe(topic)

def on_message(client, userdata, msg):
    print(msg.topic, msg.payload)
    payload = msg.payload.decode()
    data = json.loads(payload)

    print("Topic:", msg.topic)
    print("Decoded JSON keys:", data.keys())

    # Example: show fields
    # print("DevEUI:", data["devEui"])
    print("FCnt:", data["fCnt"])
    print("Payload (base64):", data["data"], "decoded", base64.b64decode(data["data"]).hex())
client = mqtt.Client(transport="websockets")
client.on_connect = on_connect
client.on_message = on_message

client.connect("chirpstack.alora-one.com", 9001)
client.loop_forever()