#!/usr/bin/env python3
# Script fourni par l'enseignant (chirpstack_mqtt_over_ws.py),
# complété pour la partie 7 :
#   Q1 : topic adapté à notre carte                      (lignes marquées Q1)
#   Q2 : décodage de la trame                            (lignes marquées Q2)
#   Q3 : graphes en temps réel avec matplotlib           (lignes marquées Q3)

import paho.mqtt.client as mqtt
import json
import base64
import threading                      # Q3
from datetime import datetime         # Q3
import matplotlib.pyplot as plt       # Q3
import matplotlib.dates as mdates     # Q3

# Q1 : topic de notre carte (application ChirpStack + DevEUI)
topic = "application/0dc3fcd5-269f-4835-9fcb-ea6ab18efe10/device/8cf957200000f639/event/up"
# topic="application/<chirpstack-application-id>/device/<device-id>/event/up"

# Q2 : identifiants de blocs (les mêmes que LPP_DATATYPE_... dans master_app.c)
LPP_DIGITAL_INPUT    = 0x00   # batterie, 1 octet, en %
LPP_TEMPERATURE      = 0x67   # température, 2 octets signés, en déci-degrés
LPP_HUMIDITY         = 0x68   # humidité, 1 octet, en demi-pourcents
LPP_BAROMETER        = 0x73   # pression, 2 octets, en daPa
LPP_FRAME_IDENTIFIER = 0x99   # identifiant de groupe, texte

# Q3 : mesures reçues (partagées entre le thread MQTT et l'affichage)
lock = threading.Lock()
heures, temperatures, humidites, pressions, batteries = [], [], [], [], []


# Q2 : décodage de la trame, bloc par bloc : [numéro][type][taille][données]
def decode_trame(trame):
    mesures = {}
    i = 0
    while i + 3 <= len(trame):
        numero, type_bloc, taille = trame[i], trame[i + 1], trame[i + 2]
        donnees = trame[i + 3:i + 3 + taille]
        i += 3 + taille

        if type_bloc == LPP_FRAME_IDENTIFIER:
            mesures["groupe"] = donnees.decode("ascii")
        elif type_bloc == LPP_TEMPERATURE:   # Big Endian, signé, ÷10 -> °C
            mesures["temperature"] = int.from_bytes(donnees, "big", signed=True) / 10
        elif type_bloc == LPP_HUMIDITY:      # demi-pourcents ÷2 -> %
            mesures["humidite"] = donnees[0] / 2
        elif type_bloc == LPP_BAROMETER:     # daPa ÷10 -> hPa
            mesures["pression"] = int.from_bytes(donnees, "big") / 10
        elif type_bloc == LPP_DIGITAL_INPUT: # batterie en %
            mesures["batterie"] = donnees[0]
    return mesures


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

    # Q2 : décodage de notre trame
    trame = base64.b64decode(data["data"])
    m = decode_trame(trame)
    print("  Groupe      :", m.get("groupe"))
    print("  Température :", m.get("temperature"), "°C")
    print("  Humidité    :", m.get("humidite"), "%")
    print("  Pression    :", m.get("pression"), "hPa")
    print("  Batterie    :", m.get("batterie"), "%")

    # Q3 : mémorisation pour les graphes
    if "temperature" in m:
        with lock:
            heures.append(datetime.now())
            temperatures.append(m.get("temperature"))
            humidites.append(m.get("humidite"))
            pressions.append(m.get("pression"))
            batteries.append(m.get("batterie"))

client = mqtt.Client(transport="websockets")
client.on_connect = on_connect
client.on_message = on_message

client.connect("chirpstack.alora-one.com", 9001)
# Q3 : la réception MQTT tourne en arrière-plan (au lieu de loop_forever())
#      pour laisser le programme principal dessiner les graphes
client.loop_start()

# Q3 : graphes en temps réel
plt.ion()
fig, grille = plt.subplots(2, 2, figsize=(11, 8))   # 2 lignes x 2 colonnes
axes = grille.flatten()                               # [haut-gauche, haut-droite, bas-gauche, bas-droite]
fig.suptitle("Capteurs LoRa - groupe RO_MQ")
titres = ["Température (°C)", "Humidité (%)", "Pression (hPa)", "Batterie (%)"]
couleurs = ["tab:red", "tab:blue", "tab:green", "tab:orange"]

while plt.fignum_exists(fig.number):        # tant que la fenêtre est ouverte
    with lock:
        series = [list(temperatures), list(humidites), list(pressions), list(batteries)]
        x = list(heures)
    for ax, titre, y, couleur in zip(axes, titres, series, couleurs):
        ax.clear()
        ax.plot(x, y, marker="o", color=couleur)
        ax.set_title(titre)
        ax.set_xlabel("Heure de réception")
        ax.grid(True)
        ax.ticklabel_format(axis="y", useOffset=False)   # vraies valeurs (pas de +1.019e3)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M:%S"))
        ax.tick_params(axis="x", rotation=30)
    fig.tight_layout()
    plt.pause(1)                             # redessine toutes les secondes

client.loop_stop()
client.disconnect()