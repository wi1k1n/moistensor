import re

def parseMessage(msg: str) -> dict:
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