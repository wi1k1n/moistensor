from protocolHandler import parsePacket
from typing import Dict, List, Set
from remoteDevice import (
    RemoteDevice,
    RemotePacket,
    RemotePacketCalibration,
    RemotePacketMeasurement,
    RemotePacketError
)

class PacketEntry:
    def __init__(self, packet: RemotePacket):
        self.packet: RemotePacket = packet

class DeviceManager:
    def __init__(self):
        self.devices: Dict[RemoteDevice, List[PacketEntry]] = dict()

    def handleMessageReceived(self, msg: str) -> RemotePacket:
        packet = parsePacket(msg)
        if type(packet) == RemotePacketError:
            print('Error when parsing packet: {0}'.format(packet.msg))

        if not (packet.remoteDevice in self.devices):
            self.devices[packet.remoteDevice] = []
        self.devices[packet.remoteDevice].append(packet)
        return packet