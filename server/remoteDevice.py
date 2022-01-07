import datetime as dt

class RemoteDevice:
    def __init__(self, id):
        self.id = id
        self.lastVoltage: int = 0
        self.voltageMin: int = 0
        self.voltageMax: int = 0
        self.lastMeasurement: int = 0
        self.calibrationDry: int = 0
        self.calibrationWet: int = 0
        self.lastTimeSpanReported: int = 0
        self.intervalIdx: int = 0
        self.interval: int = 0

        self.lastUpdateDateTime: dt.datetime = 0

    def updateMeasurement(self, v, t, m):
        self.lastVoltage = v
        self.lastMeasurement = m
        self.lastTimeSpanReported = t
        self.lastUpdateDateTime = dt.datetime.now()

    def updateCalibrations(self, v, t, Vmin, Vmax, Cdry, Cwet, intervalIdx, interval):
        self.lastVoltage = v
        self.voltageMin = Vmin
        self.voltageMax = Vmax
        self.calibrationDry = Cdry
        self.calibrationWet = Cwet
        self.lastTimeSpanReported = t
        self.intervalIdx = intervalIdx
        self.interval = interval
        self.lastUpdateDateTime = dt.datetime.now()