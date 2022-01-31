#!/usr/bin/env bash

python3 main.py \
--monitor=serial \
\#--com-port="/dev/ttyUSB0" \
--log-file=log.txt \
--database-file=db.pickle \
\
--telegram-token="YOUR_TOKEN_HERE" \
\#--bot-file=tgbot.pickle \
\
--mqtt-host="MQTT_BROKER_IP_ADDRESS" \
--mqtt-port=MQTT_BROKER_PORT \
--mqtt-user="MQTT_BROKER_USERNAME" \
--mqtt-passwd="MQTT_BROKER_PASSWORD" \
--mqtt-topic="homeassistant/sensor/HA_OBJECT_ID"