from botobj import TelegramBot
from config import TELEGRAMBOT_API
import serial

if __name__ == '__main__':
    bot = TelegramBot(TELEGRAMBOT_API)
    bot.startBot()

    print('Hello pySerial!')

    serOpen = False
    try:
        ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=10)
        print(ser.name)
        ser.flushInput()
    except:
        print('Serial could not been opened')
        serOpen = True

    while True:
        decoded_bytes = ''
        if serOpen:
            ser_bytes = ser.readline()
            decoded_bytes = ser_bytes[0:len(ser_bytes)-2].decode("utf-8")
            if not len(decoded_bytes):
                continue
            write2file = decoded_bytes.startswith('[PRv1-')
            print(('[logged]' if write2file else '') + decoded_bytes)
            if (write2file):
                with open('test.txt', 'a') as file:
                    file.write(decoded_bytes)
                bot.sendMessage(decoded_bytes)
        # except:
        #     print("Keyboard Interrupt")
        #     break