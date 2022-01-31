import re
from remoteDevice import (
    RemoteDevice,
    RemotePacket,
    RemotePacketCalibration,
    RemotePacketMeasurement,
    RemotePacketError
)

def parseMessage(msg: str) -> dict:
    """ Guarantees to return dict """
    print('parseMessage() is DEPRECATED!!!')
    preambule = re.search('\[D\d+PRv\d+-\d+\]', msg)
    if preambule:
        preambuleStr = preambule.group()
        body = msg[preambule.start() + len(preambuleStr):]

        msgDict = {
            'device': int(re.search('D\d+', preambuleStr).group()[1:]),
            'protVers': int(re.search('PRv\d+', preambuleStr).group()[3:]),
            'packetType': int(re.search('-\d+\]', preambuleStr).group()[1:-1]),
        }
        if msgDict['packetType'] == 1:  # measurement transmission
            timeSpan = re.search('t\d+(h|m)', body).group()
            msgDict['body'] = {
                'voltage': re.search('v(\d+|\?)', body).group()[1:],
                'timeSpan': int(timeSpan[1:-1]) * (1 if timeSpan[-1] == 'm' else 60),
                'measurement': int(re.search('m\d+', body).group()[1:])
            }
        elif msgDict['packetType'] == 2:  # calibration update
            timeSpan = re.search('t\d+(h|m)', body).group()
            msgDict['body'] = {
                'voltage': re.search('v(\d+|\?)', body).group()[1:],
                'timeSpan': int(timeSpan[1:-1]) * (1 if timeSpan[-1] == 'm' else 60),
                'voltageMin': re.search('vn(\d+|\?)', body).group()[2:],
                'voltageMax': re.search('vx(\d+|\?)', body).group()[2:],
                'calibrDry': int(re.search('cd\d+', body).group()[2:]),
                'calibrWet': int(re.search('cw\d+', body).group()[2:]),
                'intervalIdx': int(re.search('idx\d+', body).group()[3:]),
                'interval': int(re.search('int\d+', body).group()[3:]),
                'first': bool(re.search('f\d', body).group()[1:]),
            }
    else:
        print('[ERROR Invalid Entry]: ' + msg)
        msgDict = {'error': msg}
    return msgDict


def parsePacket(msg: str) -> RemotePacket:
    preambule = re.search('\[D\d+PRv\d+-\d+\]', msg)
    def safeParseInt(vStr: str, default: int = 0) -> int:
        n = default
        try:
            n = int(vStr)
        except:
            pass
        return n
    if preambule:
        preambuleStr = preambule.group()
        device = RemoteDevice(id=safeParseInt(re.search('D\d+', preambuleStr).group()[1:]))
        protocolVersion = safeParseInt(re.search('PRv\d+', preambuleStr).group()[3:])
        body = msg[preambule.start() + len(preambuleStr):]
        type = safeParseInt(re.search('-\d+\]', preambuleStr).group()[1:-1])
        if type == 1:  # measurement update
            timeSpan = re.search('t\d+(h|m)', body).group()
            return RemotePacketMeasurement(device, protocolVersion, type, measurement=safeParseInt(re.search('m\d+', body).group()[1:]),
                                             deviceTimeStamp=safeParseInt(timeSpan[1:-1]) * (1 if timeSpan[-1] == 'm' else 60),
                                             voltage=safeParseInt(re.search('v(\d+|\?)', body).group()[1:]))
        elif type == 2:  # calibration update
            timeSpan = re.search('t\d+(h|m)', body).group()
            return RemotePacketCalibration(device, protocolVersion, type, calibDry=safeParseInt(re.search('cd\d+', body).group()[2:]),
                                           calibWet=safeParseInt(re.search('cw\d+', body).group()[2:]),
                                           deviceTimeStamp=safeParseInt(timeSpan[1:-1]) * (1 if timeSpan[-1] == 'm' else 60),
                                           voltage=safeParseInt(re.search('v(\d+|\?)', body).group()[1:]),
                                           voltageMin=safeParseInt(re.search('vn(\d+|\?)', body).group()[2:]),
                                           voltageMax=safeParseInt(re.search('vx(\d+|\?)', body).group()[2:]),
                                           intervalIdx=safeParseInt(re.search('idx\d+', body).group()[3:]),
                                           interval=safeParseInt(re.search('int\d+', body).group()[3:]),
                                           first=bool(re.search('f\d', body).group()[1:]))
    return RemotePacketError(None, -1, -1, msg)
