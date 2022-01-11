from protocolHandler import parsePacket
import datetime as dt
from typing import Dict, List, Set, Tuple
from remoteDevice import (
    RemoteDevice,
    RemotePacket,
    RemotePacketCalibration,
    RemotePacketMeasurement,
    RemotePacketError
)

class RemoteDeviceEntry:
    def __init__(self, device: RemoteDevice):
        self.device: RemoteDevice = device
        self.entries = []
        self._latestMeasurementIdx: int = -1
        self._latestCalibrationIdx: int = -1

    def appendEntry(self, entry: RemotePacket):
        if type(entry) == RemotePacketMeasurement:
            self._latestMeasurementIdx = len(self.entries)
        if type(entry) == RemotePacketCalibration:
            self._latestCalibrationIdx = len(self.entries)
        self.entries.append(entry)

    @property
    def latestMeasurement(self) -> RemotePacket | None:
        return self.entries[self._latestMeasurementIdx] if self._latestMeasurementIdx >= 0 else None

    @property
    def latestCalibration(self) -> RemotePacket | None:
        return self.entries[self._latestCalibrationIdx] if self._latestCalibrationIdx >= 0 else None



class DeviceManager:
    def __init__(self):
        self.devices: Dict[RemoteDevice, RemoteDeviceEntry] = dict()

    def handleMessageReceived(self, msg: str) -> RemotePacket:
        packet = parsePacket(msg)
        if type(packet) == RemotePacketError:
            print('Error when parsing packet: {0}'.format(packet.msg))

        if not (packet.remoteDevice in self.devices):
            self.devices[packet.remoteDevice] = RemoteDeviceEntry(packet.remoteDevice)
        self.devices[packet.remoteDevice].appendEntry(packet)
        return packet

    def devicesOverview(self) -> List[Tuple[RemoteDevice, RemotePacketMeasurement, RemotePacketCalibration]]:
        res = []
        for (k, v) in self.devices.items():
            res.append((k, v.latestMeasurement, v.latestCalibration))
        return res