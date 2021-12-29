# Moistensor Transmitter

This is the source code for moistensor transmitter.
It consists of sensor, transmitter and MCU (Attiny85, Arduino-based or so).

## Menu navigation & LED indication

One button together with an LED (built-in) is used for the user interaction.
Main menu consists of 3 modes, which can be changed by pressing and holding button for 1s:

1. **Main mode (or Idle)** *[LED indication: (once) long + short x1]* This is the main mode, in which MCU is sleeping (to save energy) and periodically wakes up to get a measurement from the sensor and send it via RF transmitter.
    - \* Single click immediatelly transmits measurement packet (more on packets in [?transmission?]())
    - \*\* Double click resets transmission timer
2. **Calibration mode** *[LED indication: (once) long + short x2]* In this mode the calibration of the sensor can be done. (MCU will never sleep when in this mode, *although the transmissions would still happen regularly (TODO: change this to pause transmission timer while in calib-mode)*)
    - \* Single click immediatelly transmits calibration packet (more on packets in [?transmission?]())
    - \*\* Double click sets current sensor state as 'dry' threshold
    - \*\*\* Tripple click sets current sensor state as 'wet' threshold

3. **Interval mode** *[LED indication: (once) long + short x3]* In this mode the interval of periodic measurement transmissions can be chosen. (MCU will never sleep when in this mode, *although the transmissions would still happen regularly (TODO: change this to pause transmission timer while in calib-mode)*)
    - Number of clicks correspond to the following periods:
    1 -> 1m, 2 -> 15m, 3 -> 1h, 4 -> 4h, 5 -> 24h

### Extra indication cases

- LED is on during the transmission if it was initiated by user or if it has happend while the MCU was awake
- 10 very short and fast pulses designates that the MCU went to sleep (they only sent if the MCU was awake due to user interaction)

## Transmission & packets

- Transmission
- Going to sleep

## TODO list

- Add 1 bit signifying if calibration data has happened right after MCU is powered up
- No transmissions when not in MAIN mode
- LED blinking pattern notifying that calibration is not set
- Go to sleep immediately after the transmission if waking up was initiated by timer (not interrupt)
