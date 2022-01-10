# Moistensor

The arduino-based soil moisture sensor with RF transmitter.
Consists of 2 parts: transmitter (senser + transmitter) and receiver (receiver).

## Dependencies
On Arduino side:
* [TinyRF](https://github.com/pouriap/TinyRF) 433mhz RF transmission
* [EncButton](https://github.com/GyverLibs/EncButton) easier button handling
* [TimerMS](https://github.com/GyverLibs/TimerMs) easy timers
* [GyverPower](https://github.com/GyverLibs/GyverPower) easier power saving stuff
* [TimerLED](https://github.com/wi1k1n/TimerLED) easy LED interaction

On Python-server side:
* [Click](https://github.com/pallets/click/) easy arguments processing
* [Python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) easy Telegram-bot stuff
* [pySerial](https://github.com/pyserial/pyserial) serial ports manipulation

## Moistensor Transmitter

[Moistensor Transmitter Readme](433mhz_tx/)

## Moistensor Receiver

[Moistensor Receiver Readme](433mhz_rx/)

## Known bugs (aka TODOs)
* Rx & Tx use different copies of TinyRF library
* TinyRF skips same packets
* 'first' flag parsed in a wrong way on server side
