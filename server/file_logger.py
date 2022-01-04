#!/usr/bin/env python3
import time
import serial
import io

print('Hello pySerial!')

ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=10)
print(ser.name)

ser.flushInput()
while True:
    # try:
    ser_bytes = ser.readline()
    decoded_bytes = ser_bytes[0:len(ser_bytes)-2].decode("utf-8")
    if not len(decoded_bytes):
        continue
    write2file = decoded_bytes.startswith('[PRv1-')
    print(('[logged]' if write2file else '') + decoded_bytes)
    if (write2file):
        with open('data/test.old.txt', 'a') as file:
            file.write(decoded_bytes)
    # except:
    #     print("Keyboard Interrupt")
    #     break
