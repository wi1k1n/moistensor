import paho.mqtt.client as mqtt
import json
from remoteDevice import (
    RemoteDevice,
    RemotePacket,
    RemotePacketCalibration,
    RemotePacketMeasurement,
    RemotePacketError
)

class MQTTBridge:
    def __init__(self, mqtt_host, mqtt_port, mqtt_topic, mqtt_user, mqtt_passwd, timeout=60):
        self.host = mqtt_host
        self.port = mqtt_port
        self.topic = mqtt_topic
        self.topicConfig = mqtt_topic + '/config'
        self.topicState = mqtt_topic + '/state'
        self.user = mqtt_user
        self.passwd = mqtt_passwd
        self.timeout = timeout

    def openBridge(self):
        def on_connect(client, userData, flags, rc):
            print('[MQTT-Bridge] Connected with result code {0}'.format(rc))
        def on_disconnect(client, userData, rc):
            print('[MQTT-Bridge] Disconnected with result code {0}'.format(rc))
        def on_message(client, userData, msg):
            print("[MQTT-Bridge] '{0}': {1}".format(msg.topic, msg.payload))

        self.client: mqtt.Client = mqtt.Client(clean_session=True)
        self.client.on_connect = on_connect
        self.client.on_message = on_message
        self.client.on_disconnect = on_disconnect

        if all([self.user, self.passwd]):
            self.client.username_pw_set(self.user, self.passwd)

        if self.client.connect(self.host, self.port, self.timeout) == mqtt.MQTT_ERR_SUCCESS:
            self.client.loop_start()
            payload = {
                'name': 'Moistensor #9',
                'state_topic': self.topicState,
                'state_class': 'measurement',
                'value_template': '{{ value_json.measurement }}'
            }
            self.client.publish(self.topicConfig, json.dumps(payload))
            print('[MQTT-Bridge] Bridge opened')
        else:
            print('[MQTT-Bridge] Error while opening bridge')

    def closeBridge(self):
        if self.client.is_connected():
            self.client.disconnect()
        self.client.loop_stop()

    def handlePacketReceived(self, packet: RemotePacket):
        if type(packet) == RemotePacketMeasurement:
            payload = json.dumps(packet, default=lambda o: o.__dict__ if hasattr(o, '__dict__') else str(o), sort_keys=True)
            self.client.publish(self.topicState, payload)
        else:
            print('[MQTT-Bridge] packet type is {0} - is not transmitted!'.format(type(packet)))