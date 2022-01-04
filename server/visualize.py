import re, numpy as np
import matplotlib, matplotlib.pyplot as plt
matplotlib.use('Qt5Agg')

FILEPATH = 'data/test.txt'

with open(FILEPATH) as file:
    rawLines = file.readlines()

# Find last calibration entry
reCDry = re.compile('Calibration_dry: \d+')
reCWet = re.compile('Calibration_wet: \d+')
calibIndices = [(i, (re.search('\d+', reCDry.search(l).group()).group(), re.search('\d+', reCWet.search(l).group()).group()))
                for i, l in enumerate(rawLines) if re.search('[PRv1-2]', l) and reCDry.search(l) and reCWet.search(l)]

startInd = 0  # Index of last calibration line
if len(calibIndices):
    calibIndices.reverse()
    lastCalib = calibIndices[0]
    for clind in calibIndices:
        if clind[1] != lastCalib[1]:
            break
        startInd = clind[0]
else:
    print('WARNING: no calibration lines!!!')

# Get and process valid lines
lines = [l for l in rawLines[startInd:] if re.search('\[PRv1-1\]', l)]
tokens = [[i, re.search('Timestamp: \d+(m|h)', l).group()[11:], int(re.search('Measurement\*: \d+', l).group()[14:])] for i, l in enumerate(lines)]
mlts = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}
# l = np.array([[i, int(dur[:-1]) * mlts[dur[-1]], int(v)] for i, (dur, v) in enumerate(list(map(tuple, [t[37:].split(' Measurement*: ') for t in contentList])))])

x = np.array(tokens)[:, 0]
y = np.array(tokens)[:, 2]
plt.plot(x, y)
plt.show()