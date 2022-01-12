import datetime as dt

class RemoteDevice:
    def __init__(self, id: int):
        self.id: int = id

    def __eq__(self, other):
        if type(other) == RemoteDevice:
            return self.id == other.id
        elif type(other) == int:
            return self.id == other

    def __hash__(self):
        return self.id.__hash__()

    def __str__(self):
        return 'Device#{0}'.format(self.id)

class RemotePacket:
    def __init__(self, remoteDevice: RemoteDevice, protoclVersion: int, type: int, datetime: dt.datetime=None):
        self.remoteDevice: RemoteDevice = remoteDevice
        self.protocolVersion: int = protoclVersion
        self.type: int = type
        self.timestamp: dt.datetime = datetime if datetime else dt.datetime.now()

    def __str__(self):
        return '[{3} {0} PRv{1} Type:{2}]'.format(self.remoteDevice, self.protocolVersion, self.type, self.timestamp)

class RemotePacketError(RemotePacket):
    def __init__(self, remoteDevice: RemoteDevice, protoclVersion: int, type: int, msg: str):
        super().__init__(remoteDevice, protoclVersion, type)
        self.msg = msg

    def __str__(self):
        return '{0} Message - {1}'.format((RemotePacketError, self).__str__(), self.msg)

class RemotePacketMeasurement(RemotePacket):
    def __init__(self, remoteDevice: RemoteDevice, protoclVersion: int, type: int, measurement: int, deviceTimeStamp: int = 0, voltage: int = 0):
        super().__init__(remoteDevice, protoclVersion, type)
        self.measurement: int = measurement
        self.deviceTimeStamp: int = deviceTimeStamp
        self.voltage: int = voltage

    def __str__(self):
        return '{0} Measurement={1}, DeviceTimeStamp={2}, Voltage={3}'.format(super(RemotePacketMeasurement, self).__str__(),
                                                                              self.measurement, self.deviceTimeStamp, self.voltage)

class RemotePacketCalibration(RemotePacket):
    def __init__(self, remoteDevice: RemoteDevice, protoclVersion: int, type: int,
                 calibDry: int, calibWet: int, deviceTimeStamp: int = 0,
                 voltage: int = 0, voltageMin: int = 0, voltageMax: int = 0,
                 intervalIdx: int = 2, interval: int = 0, first: bool = 0):
        super().__init__(remoteDevice, protoclVersion, type)
        self.deviceTimeStamp: int = deviceTimeStamp
        self.voltage: int = voltage
        self.voltageMin: int = voltageMin
        self.voltageMax: int = voltageMax
        self.calibrationDry: int = calibDry
        self.calibrationWet: int = calibWet
        self.intervalIdx: int = intervalIdx
        self.interval: int = interval
        self.first: bool = first

    def __str__(self):
        return '{0} DevTS={1}, V={2}, Vmin={3}, Vmax={4}, CalibDry={5}, CalibWet={6}, IntIdx={7}, Interval={8}, First={9}'\
            .format(super(RemotePacketCalibration, self).__str__(), self.deviceTimeStamp, self.voltage, self.voltageMin,
                    self.voltageMax, self.calibrationDry, self.calibrationWet, self.intervalIdx, self.interval, self.first)