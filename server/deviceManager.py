import pickle, os.path as op
import warnings
from protocolHandler import parsePacket
import datetime as dt, io
from typing import Dict, List, Set, Tuple
import matplotlib, matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter
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
        self.entries: List[RemotePacket] = []
        self._latestMeasurementIdx: int = -1
        self._latestCalibrationIdx: int = -1

    def appendEntry(self, entry: RemotePacket):
        if type(entry) == RemotePacketMeasurement:
            self._latestMeasurementIdx = len(self.entries)
        if type(entry) == RemotePacketCalibration:
            self._latestCalibrationIdx = len(self.entries)
        self.entries.append(entry)

    @property
    def anyCalibration(self) -> bool:
        return self._latestCalibrationIdx >= 0
    @property
    def anyMeasurement(self) -> bool:
        return self._latestMeasurementIdx >= 0

    @property
    def latestMeasurement(self) -> RemotePacket | None:
        return self.entries[self._latestMeasurementIdx] if self.anyMeasurement else None
    @property
    def latestCalibration(self) -> RemotePacket | None:
        return self.entries[self._latestCalibrationIdx] if self.anyCalibration else None

    @property
    def measurementsSinceLatestCalibration(self) -> List[RemotePacketMeasurement]:
        if not self.anyCalibration or not self.anyMeasurement:
            return []
        return [e for e in self.entries if type(e) == RemotePacketMeasurement and e.timestamp >= self.latestCalibration.timestamp]


class DeviceManager:
    def __init__(self, filename: str | None = ''):
        self.fileName = filename if filename else ''
        self.devices: Dict[RemoteDevice, RemoteDeviceEntry] = dict()
        if filename and op.exists(filename):
            # TODO: use another database, as this is inefficient as hell if large number of entries
            with open(filename, 'rb') as file:
                self.devices = pickle.load(file)

    def handleMessageReceived(self, msg: str) -> RemotePacket:
        packet = parsePacket(msg)
        if type(packet) == RemotePacketError:
            print('Error when parsing packet: {0}'.format(packet.msg))

        if not (packet.remoteDevice in self.devices):
            self.devices[packet.remoteDevice] = RemoteDeviceEntry(packet.remoteDevice)
        self.devices[packet.remoteDevice].appendEntry(packet)

        self._updateDatabase()

        return packet

    def _updateDatabase(self):
        if not self.fileName:
            return
        with open(self.fileName, 'wb') as file:
            pickle.dump(self.devices, file)

    def deviceGraphMeasurements(self, device: RemoteDevice | int) -> io.BytesIO:
        deviceEntry = self.devices[device]
        packets = deviceEntry.measurementsSinceLatestCalibration

        x = [p.timestamp for p in packets]
        y = [p.measurement for p in packets]
        with warnings.catch_warnings():  # suppressing userwarning: running matplotlib not in main thread
            warnings.filterwarnings('ignore')
            fig, ax = plt.subplots()
        ax.plot(x, y)

        myFmt = DateFormatter("%m-%d %H:%M")
        ax.xaxis.set_major_formatter(myFmt)
        fig.autofmt_xdate()

        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)

        return buf