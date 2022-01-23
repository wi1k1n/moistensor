import math

import serial, time
from collections.abc import Callable
from util import listSerialPorts
from deviceManager import DeviceManager


class DataObtainer:
    """ Base class for receiving data from remote devices """
    def __init__(self):
        pass

    def setup(self, *args, **kwargs) -> None:
        pass

    def listen(self, callback: Callable[[str], None], blockthread: bool = False) -> None:
        pass


class DebugMonitor(DataObtainer):
    def __init__(self, interval: float = 5, type: str = 'sine'):
        self.interval = interval
        if type.lower() == 'sine':
            self.fn = lambda x: 150 * (0.5 * math.sin(0.03 * x) + 0.5) + 200
        else:
            raise NotImplemented('The \'{0}\' type of signal is not implemented'.format(type))

    def listen(self, callback: Callable[[str], None], blockthread: bool = True) -> None:
        if not blockthread:
            raise NotImplemented('Non-blocking behavior is not implemented yet')

        time.sleep(self.interval)
        callback('[D9PRv1-2] v? t0m vn? vx? cd350 cw200 idx0 int{0} f1'.format(self.interval))
        time.sleep(self.interval)
        startTime = time.time()
        while True:
            deltat = time.time() - startTime
            callback('[D9PRv1-1] v? t{0}m m{1}'.format(int(deltat / 60), self.fn(deltat)))
            time.sleep(self.interval)

class SerialMonitor(DataObtainer):
    def __init__(self):
        super().__init__()
        self.port = None
        self.baudRate = None
        self.timeout = None

    def setup(self, port: str = None, baudrate: int = 115200, timeout: int = 10) -> bool:
        """ Takes control of the thread for setting up the """
        self.port = None
        self.baudRate = baudrate
        self.timeout = timeout

        ports = listSerialPorts()
        if not len(ports):
            print('No Serial ports available')
            return False

        def portSelected(p) -> bool:
            print('Port ' + p + ' selected')
            self.port = p
            return True
        def portNotAvailable() -> bool:
            print('Port ' + self.port + ' is not available!')
            return False

        if len(ports) == 1:
            if self.port and ports[0].lower() != self.port.lower():  # the only available port mismatch requested port
                return portNotAvailable()
            if self.port:  # requested port matches the only available one
                return portSelected(ports[0])
            else:  # no requested port and only one available
                print('Selected the only available port: ' + ports[0])
                self.port = ports[0]
            return True

        if self.port:  # port requested
            reqAvail = [i for i, p in enumerate(ports) if p.lower() == self.port.lower()]
            if not len(reqAvail):  # no port from list of available ports match the requested one
                return portNotAvailable()
            return portSelected(ports[reqAvail[0]])  # requested port has been found

        # port is not requested
        print('The following ports are available:')
        for i, p in enumerate(ports):
            print('[' + str(i) + '] ' + p)
        print('X - to exit')
        print('Choose correct port (0-' + str(len(ports) - 1) + '): ', end='')
        inp = input()
        try:
            inp = int(inp)
        except:
            inp = -1
        if inp >= 0 or inp < len(ports):
            self.port = ports[inp]
            print('Port ' + self.port + ' has been chosen!')
            return True
        else:
            print('Port selection failed')
        return False

    def listen(self, callback: Callable[[str], None], blockthread: bool = True) -> None:
        """ Blocking function that listens for serial port """
        if not blockthread:
            raise NotImplemented('Non-blocking version if not implemented yet')

        ser = None
        try:
            ser = serial.Serial(self.port, self.baudRate, timeout=self.timeout)
        except:
            print('Serial could not been opened')

        if ser and ser.isOpen():
            print(ser.name)
            ser.flushInput()
            while True:
                # try:
                    msg = ser.readall().decode('utf-8')
                    if not msg:
                        continue
                    # print('Received: ' + msg)
                    if callback:
                        callback(msg)
                # except KeyboardInterrupt:
                #     break
                # except:
                #     print('Error while reading Serial port')


class HomeAssistantObtainer(DataObtainer):
    def __int__(self):
        raise NotImplemented()