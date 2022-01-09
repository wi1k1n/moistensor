import re, numpy as np, datetime as dt, io
import matplotlib, matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter
from protocolHandler import parseMessage
matplotlib.use('Qt5Agg')

def parseLogFile(path: str, devices: list = None) -> set:
    data = dict()

    reTimeStamp = re.compile('^\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2}\.\d{1,6}\t')
    with open(path) as file:
        for line in file:
            curTimeStamp = reTimeStamp.search(line)
            if curTimeStamp:
                line = line[len(curTimeStamp.group()):]
                curTimeStamp = dt.datetime.strptime(curTimeStamp.group().strip(), '%Y-%m-%d %H:%M:%S.%f')
            else:
                curTimeStamp = None
            packet = parseMessage(line)
            if not packet or 'error' in packet:
                continue
            try:
                device = packet['device']
                if devices and not (device in devices):
                    continue
                if not (device in data):
                    data[device] = []
                entry = {
                    'timestamp': curTimeStamp,
                    'packetType': packet['packetType'],
                    **packet['body']
                }
                data[device].append(entry)
            except:
                continue
    return data if len(data) else None

FILEPATH = 'data/test.txt'

data = parseLogFile(FILEPATH)
if not len(data):
    print('No devices loaded! Check your data file!')

# Sort out all entries with the outdated calibration
for i, (dev, val) in enumerate(data.items()):
    data[dev] = sorted(val, key=lambda d: d['timestamp'])
    calibs = [(v, i) for i, v in enumerate(val) if v['packetType'] == 2]
    if not len(calibs):
        print('No calibration entries for device#{0}'.format(dev))
        data[dev] = ([e for e in data[dev] if e['packetType'] == 1], None)
        continue
    calibs.reverse()
    lCalibIdx = 0  # last calibration index
    for j, c in enumerate(calibs):
        if c[0]['calibrDry'] != calibs[lCalibIdx][0]['calibrDry'] or c[0]['calibrWet'] != calibs[lCalibIdx][0]['calibrWet']:
            break
        lCalibIdx = j
    calibration = calibs[lCalibIdx][0]
    startIndex = calibs[lCalibIdx][-1]
    data[dev] = ([e for k, e in enumerate(data[dev]) if k > startIndex and e['packetType'] == 1], calibration)

for (dev, (l, calibr)) in data.items():
    x = [e['timestamp'] for e in l]
    y = [e['measurement'] for e in l]
    fig, ax = plt.subplots()
    ax.plot(x, y)

    myFmt = DateFormatter("%m-%d %H:%M")
    ax.xaxis.set_major_formatter(myFmt)
    fig.autofmt_xdate()

    plt.savefig('t.png')
    # plt.show()

    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)

    # print(len(buf))