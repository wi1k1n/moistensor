import re, numpy as np
import matplotlib, matplotlib.pyplot as plt
matplotlib.use('Qt5Agg')

FILEPATH = 'test.txt'

with open(FILEPATH) as file:
    content = ''.join(file.readlines())
contentList = re.findall('\[PRv1-1\] Voltage: unknown Timestamp: \d+[smhd] Measurement\*: \d+', content)
mlts = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}
l = np.array([[i, int(dur[:-1]) * mlts[dur[-1]], int(v)] for i, (dur, v) in enumerate(list(map(tuple, [t[37:].split(' Measurement*: ') for t in contentList])))])

plt.plot(l[:, 0], l[:, 2])
plt.show()