#include <EncButton.h>
#include <TimerLED.h>
#include <TimerMs.h>
#include "src/TinyRF/TinyRF_TX.h" // add ../TinyRF to the list of include paths for this to work
#include <GyverPower.h>
#include <EEPROM.h>

#define DEBUG
#ifdef DEBUG
#define DEBUG_SERIAL
#endif

const uint8_t DEVICE_ID = 9; // (0 .. 31) transmitted every time for receiver to distinguish between different devices
const uint8_t PROTOCOL_VERSION = 1; // (0 .. 7)

const uint8_t TX_REPEAT_MSG = 10;
#define PACKET_1_SIZE 4
#define PACKET_2_SIZE 6

//const int PIN_TX = 12; // hardcoded in tinyrf
const uint8_t PIN_LED = 13;
const uint8_t PIN_BTN = 3; // should be an interrupt pin (D2/D3 for Uno/Nano/ProMini)
const uint8_t BTN_INTERRUPT = 1; // 0 if D2, 1 if D3
const uint8_t PIN_SENSOR = A2;

EncButton<EB_TICK, PIN_BTN> btn;
TimerLED timerLed(PIN_LED, true, false);
TimerMs timerIdleToSleep(5000, 0, 1);
TimerMs timerTransmit;

#define MODE_MAIN     0
#define MODE_CALIB    1
#define MODE_INTERVAL 2

const uint16_t    MODE_LED[] = {750, 250, 250, 250, 250, 250, 250, 250};
const uint8_t     MODE_LED_MAIN_LEN = 4;
const uint8_t     MODE_LED_CALIB_LEN = 6;
const uint8_t     MODE_LED_INTERVAL_LEN = 8;

const uint16_t    MODE_INTERVAL_LED[] = {250, 250, 250, 250, 250, 250, 250, 250, 250, 250};
const uint16_t    MODE_INTERVAL_DURATIONS[] = {1, 15, 60, 240, 1440}; // in minutes
const uint8_t     MODE_INTERVAL_DURATIONS_LEN = 5;

const uint16_t*   MODE_CALIBRATION_LED = MODE_INTERVAL_LED;

const uint16_t    GOSLEEP_LED[] = {20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20};
const uint8_t     GOSLEEP_LED_LEN = 20;

#define EEPROM_IDX_THRESHOLD_DRY          5
#define EEPROM_IDX_THRESHOLD_WET          6
#define EEPROM_IDX_INTERVAL_DURATION_IDX  7



uint8_t mode = MODE_MAIN;
uint8_t intervalDurationIdx = 2;
uint8_t sensorThresholdDry = 50; // (0 .. 63)
uint8_t sensorThresholdWet = 40; // (0 .. 63)
uint8_t sensorLastMeasurement = 0; // (0 .. 63)

volatile bool isSleeping = false;
volatile bool needToAutoLed = true; // if we need to blink when transmitting/sleeping (only happens after btn interrupt)
bool needToSendCalibrations = false; // if calibration need to be transmitted before going to sleep

uint8_t millisRolloverCount = 0;
bool millisRolloverListening = false;
uint8_t* txBuffer = new uint8_t[max(PACKET_1_SIZE, PACKET_2_SIZE)];



void setupTX() {
  setupTransmitter();
  uint8_t b0 = DEVICE_ID << 3;
  b0 |= PROTOCOL_VERSION;
  txBuffer[0] = b0;
}

void makeMeasurement() {
  sensorLastMeasurement = map(analogRead(PIN_SENSOR), 0, 1023, 0, 63);
#ifdef DEBUG_SERIAL
  Serial.print(F("makeMeasurement(): "));
  Serial.println(sensorLastMeasurement);
#endif
}

#ifdef DEBUG_SERIAL
void hexBinDump(const uint8_t* buf, const uint8_t& len);
#endif

// Calculate unit (s/m/h/d) and corresponding value of time in these units
void retrieveTimeSinceStarted(uint8_t& _unit, uint16_t& _time) {
  uint32_t time = millis() / 1000 + (uint32_t)(millisRolloverCount * 4294967.296f); // in seconds
  const uint8_t devisors[] = {60, 60, 24}; // divisors to sequentially get minutes, hours and days
  uint8_t i = 0;
  do {
    if (time < 1024) {
      _unit = i;
      _time = time;
      return;
    } else if (i == 3) { // if bigger than 1023 days, then clamp to 1024 days
        _unit = 3;
        _time = 1023;
        return;
    }
    time /= devisors[i];
  } while (++i <= 3);
}

void transmit(const uint8_t& len) {
#ifdef DEBUG_SERIAL
  Serial.print(F("Transmitting packet: "));
  hexBinDump(txBuffer, len);
#endif
  // time margin between transmissions
  // delayMicroseconds(TX_DELAY_MICROS);

  if (needToAutoLed)
    digitalWrite(PIN_LED, HIGH);
  sendMulti((byte*)txBuffer, len, TX_REPEAT_MSG);
  if (needToAutoLed)
    digitalWrite(PIN_LED, LOW);
#ifdef DEBUG_SERIAL
  Serial.println(F("# Transmitted"));
#endif
}

// Protocol v1
// DEVICE_ID        5 bits  (0 .. 31)
// prot_version     3 bits  (0 .. 7)
// packet_type      3 bits  (0 .. 7)
//
// packet_type == 1: sensor measurement
// voltage          3 bits  (0 .. 7)      0 - unknown
// unit             2 bits  (0 .. 3)      0 - seconds, 1 - minutes, 2 - hours, 3 - days
// timestamp        10 bits (0 .. 1023)   time since device started in units
// sensor_val       6 bits  (0 .. 63)
// |       b0             |  |           b1           | |     b2      | |      b3      |
// x x x x x  x     x     x  x    x    x   x  x  x x  x x x x x x x x x x x  x x x x x x
// DEVICE_ID  prot_version   packet_type   voltage unit timestamp_in_s/m/h/d  sensor_val
void transmitLastMeasurement() {
  uint8_t unit;
  uint16_t time;
  retrieveTimeSinceStarted(unit, time);

  uint8_t b1 = 1 << 5; // packet_type = 1
  // b1 |= 0 << 2; // voltage unknown for now
  b1 |= unit & 0b11; // add units
  uint8_t b2 = time >> 2 & 0xFF; // add big part of timestamp
  uint8_t b3 = (time & 0b11) << 6; // add little part of timestamp
  b3 |= sensorLastMeasurement & 0b111111;

  txBuffer[1] = b1;
  txBuffer[2] = b2;
  txBuffer[3] = b3;
  
  transmit(PACKET_1_SIZE);
}

// packet_type == 2: share calibration data
// voltage          3 bits  (0 .. 7)      0 - unknown
// unit             2 bits  (0 .. 3)      0 - seconds, 1 - minutes, 2 - hours, 3 - days
// timestamp        10 bits (0 .. 1023)   time since device started in units
// V_min            3 bits  (0 .. 7)      0 - unknown; minimum voltage
// V_max            3 bits  (0 .. 7)      0 - unknown; maximum voltage
// Clbrtn__dry      6 bits  (0 .. 63)     calibration threshold for 'dry'
// Clbrtn__wet      6 bits  (0 .. 63)     calibration threshold for 'wet'
// Intrvl           3 bits  (0 .. 7)      index of interval for transmitting sensor measurements
// NAS                                    Not Assigned
// |       b0             | |           b1           | |     b2      | |      b3      | |     b4      | |       b5      |
// x x x x x  x     x     x x    x    x   x  x  x x  x x x x x x x x x x x  x x x x x x x x x x x x x x x x x x x x x   x
// DEVICE_ID  prot_version  packet_type   voltage unit timestamp_in_s/m/h/d V_min V_max Clbrtn__dry Clbrtn__wet Intrvl NAS
void transmitCalibration() {
  uint8_t unit;
  uint16_t time;
  retrieveTimeSinceStarted(unit, time);
  
  uint8_t b1 = 2 << 5; // packet_type = 1
  // b1 |= 0 << 2; // TODO: voltage unknown for now
  b1 |= unit & 0b11; // add units
  uint8_t b2 = time >> 2 & 0xFF; // add big part of timestamp
  uint8_t b3 = (time & 0b11) << 6; // add little part of timestamp
  // b3 |= 0 << 3; // TODO: V_min unknown for now
  // b3 |= 0; // TODO: V_max unknown for now
  uint8_t b4 = (sensorThresholdDry & 0b111111) << 2; // add calibration for 'dry'
  b4 |= (sensorThresholdWet & 0b111111) >> 4;
  uint8_t b5 = (sensorThresholdWet & 0b1111) << 4;
  b5 |= (intervalDurationIdx & 0b111) << 1;

  txBuffer[1] = b1;
  txBuffer[2] = b2;
  txBuffer[3] = b3;
  txBuffer[4] = b4;
  txBuffer[5] = b5;
  
  transmit(PACKET_2_SIZE);
}

void measureAndTransmit() {
  makeMeasurement();
  transmitLastMeasurement();
}

void millisRolloverHandle() {
  if (!millisRolloverListening) {
    if (millis() > 0x7FFFFFFFL) {
      millisRolloverListening = true;
    }
  } else {
    if (millis() < 0x7FFFFFFFL) {
      millisRolloverCount++;
      millisRolloverListening = false;
    }
  }
}

void handleWakeUp() {
  if (!isSleeping)
    return;
  detachInterrupt(BTN_INTERRUPT);
  isSleeping = false;
  needToAutoLed = true;
  power.wakeUp();
#ifdef DEBUG_SERIAL
  Serial.println("# Interrupt Fired!");
#endif
}

void goToSleep() {
  // send calibrations if smth has been changed
  if (needToSendCalibrations) {
    transmitCalibration();
    needToSendCalibrations = false;
  }

  if (needToAutoLed) {
    // flash with led
    for (uint8_t i = 0; i < GOSLEEP_LED_LEN; ++i) {
      digitalWrite(PIN_LED, i % 2 ? HIGH : LOW);
      delay(GOSLEEP_LED[i]);
    }
    digitalWrite(PIN_LED, LOW);
  }
  
  prepareForSleep();
  attachInterrupt(BTN_INTERRUPT, handleWakeUp, LOW);
#ifdef DEBUG_SERIAL
  Serial.print(F("# Going to sleep for ~"));
  Serial.print(timerTransmit.timeLeft() / 1000);
  Serial.println(F(" seconds"));
  delay(20);
#endif
      uint32_t timeLeftBeforeTx = timerTransmit.timeLeft();
      isSleeping = true;
      needToAutoLed = false;
      power.sleepDelay(timeLeftBeforeTx);

      // Continue here when woke up
      timerIdleToSleep.restart();
      if (isSleeping) {
        // Here, if woke up by ourselves (not by interrupt)
        isSleeping = false;
      }
#ifdef DEBUG_SERIAL
  Serial.println("# Just woke up!");
#endif
}

void prepareForSleep() {
  btn.resetState();
  timerLed.stop();
  timerIdleToSleep.stop();
}

void loadFromEEPROM() {
  // Retrieve sevsor thresholds
  uint8_t _dry = EEPROM.read(EEPROM_IDX_THRESHOLD_DRY),
          _wet = EEPROM.read(EEPROM_IDX_THRESHOLD_WET);
#ifdef DEBUG_SERIAL
  Serial.print(F("loadFromEEPROM() loaded: dry = "));
  Serial.print(_dry);
  Serial.print(F("; wet = "));
  Serial.println(_wet);
#endif
  // Validate sensor thresholds
  if (_wet < _dry && _wet < 64 && _dry < 64) {
    sensorThresholdDry = _dry;
    sensorThresholdWet = _wet;
  }
  else {
#ifdef DEBUG_SERIAL
  Serial.print(F("loadFromEEPROM() WARNING: validation failed - dry = "));
  Serial.print(sensorThresholdDry);
  Serial.print(F("; wet = "));
  Serial.println(sensorThresholdWet);
#endif
  }
  // Retrieve interval index
  uint8_t _interval = EEPROM.read(EEPROM_IDX_INTERVAL_DURATION_IDX);
#ifdef DEBUG_SERIAL
  Serial.print(F("loadFromEEPROM() loaded: [idx] = ["));
  Serial.print(_interval);
  Serial.print(F("]"));
#endif
  // Validate interval index
  if (_interval < MODE_INTERVAL_DURATIONS_LEN) {
    intervalDurationIdx = _interval;
#ifdef DEBUG_SERIAL
  Serial.print(F(" interval = "));
  Serial.println(MODE_INTERVAL_DURATIONS[intervalDurationIdx]);
#endif
  } else {
#ifdef DEBUG_SERIAL
  Serial.println();
  Serial.print(F("loadFromEEPROM() WARNING: validation failed - [idx] interval = ["));
  Serial.print(intervalDurationIdx);
  Serial.print(F("] "));
  Serial.println(MODE_INTERVAL_DURATIONS[intervalDurationIdx]);
#endif
  }
  // Transmit all the calibrations after they are loaded
  transmitCalibration();
}

void blinkLed(const uint8_t &len, const uint16_t *intervals) {
  timerLed.setIntervals(len, intervals);
  timerLed.restart();
}

void handleMenuMain() {
  // Update goToSleepTimer every time btn is down in mode MAIN
  if (btn.state()) {
    timerIdleToSleep.restart();
  }
  if (btn.hasClicks(1)) {
    // Send current data once
    measureAndTransmit();
  }
  if (btn.hasClicks(2)) {
    // Restart measuring and transmitting interval
    timerTransmit.restart();
#ifdef DEBUG_SERIAL
    Serial.print(F(" => Transmission Timer restarted. millis() = "));
    Serial.println(millis());
#endif
  }
  // if (btn.hasClicks(3)) {
  //   // something else (forgot what wanted to put here)
  // }
}

void handleMenuCalibration() {
  if (btn.hasClicks()) {
    if (btn.clicks > 1 && btn.clicks < 4) {
      blinkLed(btn.clicks * 2, MODE_INTERVAL_LED);
      makeMeasurement();
      if (btn.clicks == 2) {
        sensorThresholdDry = sensorLastMeasurement;
        EEPROM.write(EEPROM_IDX_THRESHOLD_DRY, sensorThresholdDry);
        needToSendCalibrations = true; // calibrations will be transmitted before going to sleep
#ifdef DEBUG_SERIAL
        Serial.print(F("dry value updated: "));
#endif
      }
      else {
        sensorThresholdWet = sensorLastMeasurement;
        EEPROM.write(EEPROM_IDX_THRESHOLD_WET, sensorThresholdWet);
        needToSendCalibrations = true;
#ifdef DEBUG_SERIAL
        Serial.print(F("wet value updated: "));
#endif
      }
#ifdef DEBUG_SERIAL
    Serial.print(F("(dry: "));
    Serial.print(sensorThresholdDry);
    Serial.print(F(", wet: "));
    Serial.print(sensorThresholdWet);
    Serial.println(F(")"));
#endif
    } else if (btn.clicks == 1) {
      // Single click in calibration mode sends calibration data
      transmitCalibration();
    }
  }
}

void handleMenuInterval() {
  if (btn.hasClicks() && btn.clicks <= MODE_INTERVAL_DURATIONS_LEN) {
    blinkLed(btn.clicks * 2, MODE_INTERVAL_LED);
    intervalDurationIdx = btn.clicks - 1;
    EEPROM.write(EEPROM_IDX_INTERVAL_DURATION_IDX, intervalDurationIdx);
    timerTransmit.setTime(MODE_INTERVAL_DURATIONS[intervalDurationIdx] * 60000);
    timerTransmit.restart();
    needToSendCalibrations = true;
#ifdef DEBUG_SERIAL
    Serial.print(F("new interval (in minutes): "));
    Serial.println((uint16_t)MODE_INTERVAL_DURATIONS[intervalDurationIdx]);
#endif
  }
}

void handleMenuNext(const uint8_t nextMode, const uint8_t len, const uint16_t* intervals) {
  if (btn.held()) {
    blinkLed(len, intervals);
    mode = nextMode;
#ifdef DEBUG_SERIAL
    Serial.print(F("> mode: "));
    if (mode == MODE_MAIN)
      Serial.println(F("MAIN"));
    else if (mode == MODE_CALIB)
      Serial.println(F("CALIBRATION"));
    else if (mode == MODE_INTERVAL)
      Serial.println(F("INTERVAL"));
#endif
  }
  // Stop goToSleep timer if not in mode MAIN
  if (mode != MODE_MAIN && timerIdleToSleep.active()) {
    timerIdleToSleep.stop();
  }
}



/////////////////////////////////////////////////////////////////////////
///////////////////////////////// SETUP /////////////////////////////////
/////////////////////////////////////////////////////////////////////////
void setup() {
#ifdef DEBUG_SERIAL
  Serial.begin(115200);
  Serial.println(F("Welcome to Remote Moisture Sensing deivce!"));
#endif

  setupTX();
  pinMode(PIN_LED, OUTPUT);

  loadFromEEPROM();
  timerTransmit.attach(measureAndTransmit);
  timerTransmit.setTime(MODE_INTERVAL_DURATIONS[intervalDurationIdx] * 60000);
  timerTransmit.restart();

  // Setup sleeping stuff
  power.autoCalibrate();
  power.setSleepMode(POWERDOWN_SLEEP);

  timerIdleToSleep.attach(goToSleep);
  timerIdleToSleep.restart();

#ifdef DEBUG_SERIAL
  Serial.println(F("> mode: MAIN"));
#endif
}


/////////////////////////////////////////////////////////////////////////
////////////////////////////////// LOOP /////////////////////////////////
/////////////////////////////////////////////////////////////////////////
void loop() {

  btn.tick();
  timerLed.tick();
  timerIdleToSleep.tick();
  timerTransmit.tick();
  millisRolloverHandle(); // not tested well

  // Main mode: wake up, get measurement, send measurement, sleep
  if (mode == MODE_MAIN) {
    handleMenuNext(MODE_CALIB, MODE_LED_CALIB_LEN, MODE_LED);
    handleMenuMain();
  }
  // Calibration mode: wait for button clicks for calibration
  else if (mode == MODE_CALIB) {
    handleMenuNext(MODE_INTERVAL, MODE_LED_INTERVAL_LEN, MODE_LED);
    handleMenuCalibration();
  }
  // Interval mode: wait for button clicks to iterate over intervals
  else if (mode == MODE_INTERVAL) {
    handleMenuNext(MODE_MAIN, MODE_LED_MAIN_LEN, MODE_LED);
    handleMenuInterval();
  }
}




#ifdef DEBUG_SERIAL
void hexBinDump(const uint8_t* buf, const uint8_t& len) {
  for (int i = 0; i < len; ++i) {
    Serial.print(F("d"));
    byte mask = B10000000;
    if (buf[i] < 16) {
      Serial.print(F("0"));
    }
    Serial.print(buf[i], HEX);
    Serial.print(F("[b"));
    for (int k = 0; k < 8; ++k) {
      if (buf[i] & mask) {
        Serial.print(F("1"));
      }
      else {
        Serial.print(F("0"));
      }
      mask = mask >> 1;
    }
    Serial.print(F("] "));
  }
  Serial.println();
}
#endif