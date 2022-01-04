import serial, time
from collections.abc import Callable
from util import listSerialPorts


class DataObtainer:
    def __init__(self):
        pass

    def setup(self) -> None:
        pass

    def listen(self, callback: Callable[[str], None], blockthread: bool = False) -> None:
        pass


class DebugMonitor(DataObtainer):
    def listen(self, callback: Callable[[str], None], blockthread: bool = True) -> None:
        if not blockthread:
            raise NotImplemented('Non-blocking behavior is not implemented yet')

        startTime = time.time()
        while True:
            callback("{0} passed!".format(time.time() - startTime))
            time.sleep(10)

class SerialMonitor(DataObtainer):
    def __init__(self, port: str = None, baudrate: int = 115200, timeout: int = 10):
        super().__init__()
        self.port = port
        self.baudRate = baudrate
        self.timeout = timeout

    def setup(self) -> None:
        """ Takes control of the thread for setting up the """
        ports = listSerialPorts()
        if not len(ports):
            print('No Serial ports available')
            return False
        if len(ports) == 1:
            print('The only port available: ' + ports[0])
            self.port = ports[0]
            return True

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
            print(ser.name)
            ser.flushInput()
        except:
            print('Serial could not been opened')

        if ser and ser.isOpen():
            while True:
                try:
                    bytes = ser.readall()
                    bytesDecoded = bytes.decode('utf-8')
                    if not bytesDecoded:
                        continue
                    print('Received: ' + bytesDecoded)
                    if callback:
                        callback(bytesDecoded)
                except:
                    print('Error while reading Serial port')
