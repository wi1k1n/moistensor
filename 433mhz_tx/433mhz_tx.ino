#include <EncButton.h>
#include <TimerLED.h>
#include <TimerMs.h>
#include "src/TinyRF/TinyRF_TX.h" // add ../TinyRF to the list of include paths for this to work
#include <GyverPower.h>
#include <EEPROM.h>

#define DEBUG
// #define RESET_EEPROM_CALIBRATION

#ifdef DEBUG
#define DEBUG_SERIAL
#define SERIAL_MONITOR_WIDTH 120
#endif

const uint8_t DEVICE_ID = 9; // (0 .. 31) transmitted every time for receiver to distinguish between different devices
const uint8_t PROTOCOL_VERSION = 1; // (0 .. 7)

const uint8_t TX_REPEAT_MSG = 10;
#define PACKET_1_SIZE 5
#define PACKET_2_SIZE 8

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
#define EEPROM_IDX_THRESHOLD_WET          7
#define EEPROM_IDX_INTERVAL_DURATION_IDX  9



uint8_t mode = MODE_MAIN;
uint8_t intervalDurationIdx = 2;
uint16_t sensorThresholdDry = 800; // (0 .. 1023) raw value
uint16_t sensorThresholdWet = 600; // (0 .. 1023) raw value
volatile uint16_t sensorLastMeasurement = 0; // (0 .. 1023) raw value

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
  // sensorLastMeasurement = map(analogRead(PIN_SENSOR), 0, 1023, 0, 255);
  sensorLastMeasurement = analogRead(PIN_SENSOR);
#ifdef DEBUG_SERIAL
  Serial.print(F("makeMeasurement(): "));
  Serial.println(sensorLastMeasurement);
#endif
}

#ifdef DEBUG_SERIAL
void hexBinDump(const uint8_t* buf, const uint8_t& len);
#endif

// Calculate unit (m/h) and corresponding value of time in these units
void retrieveTimeSinceStarted(uint8_t& _unit, uint16_t& _time) {
  uint32_t time = millis() / 60000 + (uint32_t)(millisRolloverCount * 4294967.296f / 60.f); // in minutes
  if (time < 32768) {
    _unit = 0;
    _time = time;
    return;
  }
  time /= 24;
  _unit = 1;
  if (time < 32768) {
    _time = time;
    return;
  }
  _time = 32768;
  return;

  // uint32_t time = millis() / 1000 + (uint32_t)(millisRolloverCount * 4294967.296f); // in seconds
  // const uint8_t devisors[] = {60, 60, 24}; // divisors to sequentially get minutes, hours and days
  // uint8_t i = 0;
  // do {
  //   if (time < 1024) {
  //     _unit = i;
  //     _time = time;
  //     return;
  //   } else if (i == 3) { // if bigger than 1023 days, then clamp to 1024 days
  //       _unit = 3;
  //       _time = 1023;
  //       return;
  //   }
  //   time /= devisors[i];
  // } while (++i <= 3);
}

void transmit(const uint8_t& len) {
#ifdef DEBUG_SERIAL
  Serial.print(F("Transmitting packet: "));
  hexBinDump(txBuffer, len);
#endif

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
// DEVICE_ID          5 bits  (1 .. 31)
// p_ver              3 bits  (0 .. 7)
// ptype              3 bits  (0 .. 7)
//
// ptype == 1: sensor measurement
// voltg              3 bits  (0 .. 7)      0 - unknown
// u                  1 bits  (0 .. 1)      units: 0 - minutes, 1 - hours
// timestamp          15 bits (0 .. 32767)  time since device started in units
// measurement_value  10 bits (0 .. 1023)   measurement value, stretched between thresholds
// |       b0    | |     b1      | |     b2      | |     b3      | |     b4      |
// x x x x x x x x x x x x x x x x x x x x x x x x x x x x x x x x x x x x x x x x
// DEVICE_ID p_ver ptype voltg u timestamp_in_minutes_or_hours _measurement_value_
void transmitLastMeasurement() {
  uint8_t unit;
  uint16_t time;
  retrieveTimeSinceStarted(unit, time);

  uint8_t b1 = 1 << 5; // packet_type = 1
  // b1 |= 0 << 2; // voltage unknown for now
  b1 |= (unit & 1) << 1;
  b1 |= time >> 14;
  uint8_t b2 = time >> 6 & 0xFF;
  uint8_t b3 = (time & 0b111111) << 2;
  b3 |= sensorLastMeasurement >> 8 & 0b11;
  uint8_t b4 = sensorLastMeasurement & 0xFF;

  // // stretch measurement between thresholds and map to 8 bits
  // uint8_t measVal = (uint16_t)(constrain(sensorLastMeasurement, sensorThresholdWet, sensorThresholdDry) - sensorThresholdWet) * 255 / (sensorThresholdDry - sensorThresholdWet);
  // b3 |= measVal & 0b111111;

  txBuffer[1] = b1;
  txBuffer[2] = b2;
  txBuffer[3] = b3;
  txBuffer[4] = b4;
  
  transmit(PACKET_1_SIZE);
}

// ptype == 2: share calibration data
// voltg            3 bits  (0 .. 7)      0 - unknown
// u                1 bits  (0 .. 1)      units: 0 - minutes, 1 - hours
// timestamp        15 bits (0 .. 32767)  time since device started in units
// V_min            3 bits  (0 .. 7)      0 - unknown; minimum voltage
// V_max            3 bits  (0 .. 7)      0 - unknown; maximum voltage
// Meas_calibr_dry  10 bits (0 .. 1023)   calibration threshold for 'dry'
// Meas_calibr_wet  10 bits (0 .. 1023)   calibration threshold for 'wet'
// Intrvl           3 bits  (0 .. 7)      index of interval for transmitting sensor measurements
// F                1 bit   (0 .. 1)      First, if this package is sent as a part of the initialization
// NA                                     Not assigned
// |       b0    | |     b1      | |     b2      | |     b3      | |     b4      | |     b5      | |     b6      | |     b7       |
// x x x x x x x x x x x x x x x x x x x x x x x x x x x x x x x x x x x x x x x x x x x x x x x x x x x x x x x x x x x  x x x x x
// DEVICE_ID p_ver ptype voltg u timestamp_in_minutes_or_hours V_min V_max __Meas_calibr_dry__ __Meas_calibr_wet__ Intrvl F __NA___
void transmitCalibration(bool first) {
  uint8_t unit;
  uint16_t time;
  retrieveTimeSinceStarted(unit, time);
  
  uint8_t b1 = 2 << 5; // packet_type = 2
  // b1 |= 0 << 2; // TODO: voltage unknown for now
  b1 |= (unit & 1) << 1;
  b1 |= time >> 14;
  uint8_t b2 = time >> 6 & 0xFF;
  uint8_t b3 = (time & 0b111111) << 2;
  // b3 |= (0 & 0b111) >> 1; // TODO: V_min unknown for now
  uint8_t b4 = (0 & 1) << 7; // TODO: V_min unknown for now
  b4 |= (0 & 0b111) << 4; // TODO: V_max unknown for now
  b4 |= (sensorThresholdDry & 0b1111111111) >> 6;
  uint8_t b5 = (sensorThresholdDry & 0b111111) << 2;
  b5 |= (sensorThresholdWet & 0b1111111111) >> 8;
  uint8_t b6 = sensorThresholdWet & 0b11111111;
  uint8_t b7 = (intervalDurationIdx & 0b111) << 5;
  b7 |= ((uint8_t)first) << 4;

  txBuffer[1] = b1;
  txBuffer[2] = b2;
  txBuffer[3] = b3;
  txBuffer[4] = b4;
  txBuffer[5] = b5;
  txBuffer[6] = b6;
  txBuffer[7] = b7;
  
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
    transmitCalibration(false);
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
  uint8_t _interval = EEPROM.read(EEPROM_IDX_INTERVAL_DURATION_IDX);
  uint16_t _dry, _wet;
  EEPROM.get(EEPROM_IDX_THRESHOLD_DRY, _dry);
  EEPROM.get(EEPROM_IDX_THRESHOLD_WET, _wet);
#ifdef DEBUG_SERIAL
  Serial.println(F("<loadFromEEPROM()> Loaded:"));
  Serial.print(F("--> dry = ")); Serial.println(_dry);
  Serial.print(F("--> wet = ")); Serial.println(_wet);
  Serial.print(F("--> interval[idx] = ")); Serial.print(MODE_INTERVAL_DURATIONS[_interval]);
  Serial.print(F("[")); Serial.print(_interval); Serial.println(F("]"));
#endif
  // Validate sensor thresholds
  if (_wet < _dry && _wet < 1024 && _dry < 1024) {
    sensorThresholdDry = _dry;
    sensorThresholdWet = _wet;
  }
  else {
#ifdef DEBUG_SERIAL
  Serial.println(F("<loadFromEEPROM()> WARNING: range validation failed"));
  Serial.print(F("--> dry = "));
  Serial.println(sensorThresholdDry);
  Serial.print(F("--> wet = "));
  Serial.println(sensorThresholdWet);
#endif
  }
  // Validate interval index
  if (_interval < MODE_INTERVAL_DURATIONS_LEN) {
    intervalDurationIdx = _interval;
  } else {
#ifdef DEBUG_SERIAL
  Serial.println(F("<loadFromEEPROM()> WARNING: interval validation failed"));
  Serial.print(F("--> interval[idx] = ")); Serial.print(MODE_INTERVAL_DURATIONS[intervalDurationIdx]);
  Serial.print(F("[")); Serial.print(intervalDurationIdx); Serial.println(F("]"));
#endif
  }
  // Transmit all the calibrations after they are loaded
  transmitCalibration(true);
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
#ifdef DEBUG_SERIAL
    Serial.println(F("<handleMenuMain()> Event: manual transmission of measurement"));
#endif
    measureAndTransmit();
  }
  if (btn.hasClicks(2)) {
    // Restart measuring and transmitting interval
#ifdef DEBUG_SERIAL
    Serial.println(F("<handleMenuMain()> Event: button clicked for manual transmission"));
    Serial.print(F("--> millis() = "));
    Serial.println(millis());
#endif
    timerTransmit.restart();
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
        uint16_t oldDry = sensorThresholdDry;
        sensorThresholdDry = constrain(sensorLastMeasurement, 0, 1023);
        EEPROM.put(EEPROM_IDX_THRESHOLD_DRY, sensorThresholdDry);
        needToSendCalibrations = true; // calibrations will be transmitted before going to sleep
#ifdef DEBUG_SERIAL
        Serial.println(F("<handleMenuCalibration()> Event: change dry calibration"));
        Serial.print(F("--> dryOld = "));
        Serial.println(oldDry);
        Serial.print(F("--> dryNew = "));
        Serial.println(sensorThresholdDry);
#endif
      }
      else {
        uint16_t oldWet = sensorThresholdWet;
        sensorThresholdWet = constrain(sensorLastMeasurement, 0, 1023);
        EEPROM.put(EEPROM_IDX_THRESHOLD_WET, sensorThresholdWet);
        needToSendCalibrations = true;
#ifdef DEBUG_SERIAL
        Serial.println(F("<handleMenuCalibration()> Event: change wet calibration"));
        Serial.print(F("--> wetOld = "));
        Serial.println(oldWet);
        Serial.print(F("--> wetNew = "));
        Serial.println(sensorThresholdWet);
#endif
      }
#ifdef DEBUG_SERIAL
    Serial.println(F("--> current values:"));
    Serial.print(F("--> --> dry = "));
    Serial.println(sensorThresholdDry);
    Serial.print(F("--> --> wet = "));
    Serial.println(sensorThresholdWet);
#endif
    } else if (btn.clicks == 1) {
      // Single click in calibration mode sends calibration data
#ifdef DEBUG_SERIAL
    Serial.println(F("<handleMenuCalibration()> Event: manual transmission of calibrations"));
#endif
      transmitCalibration(false);
    }
  }
}

void handleMenuInterval() {
  if (btn.hasClicks() && btn.clicks <= MODE_INTERVAL_DURATIONS_LEN) {
    uint8_t intIdxOld = intervalDurationIdx;
    blinkLed(btn.clicks * 2, MODE_INTERVAL_LED);
    intervalDurationIdx = btn.clicks - 1;
    EEPROM.write(EEPROM_IDX_INTERVAL_DURATION_IDX, intervalDurationIdx);
    timerTransmit.setTime(MODE_INTERVAL_DURATIONS[intervalDurationIdx] * 60000);
    timerTransmit.restart();
    needToSendCalibrations = true;
#ifdef DEBUG_SERIAL
        Serial.println(F("<handleMenuInterval()> Event: change interval"));
        Serial.print(F("--> old[idx] = "));
        Serial.print(MODE_INTERVAL_DURATIONS[intIdxOld]);
        Serial.print(F("["));
        Serial.print(intIdxOld);
        Serial.println(F("]"));
        Serial.print(F("--> new[idx] = "));
        Serial.print(MODE_INTERVAL_DURATIONS[intervalDurationIdx]);
        Serial.print(F("["));
        Serial.print(intervalDurationIdx);
        Serial.println(F("]"));
#endif
  }
}

void handleMenuNext(const uint8_t nextMode, const uint8_t len, const uint16_t* intervals) {
  if (btn.held()) {
    blinkLed(len, intervals);
    mode = nextMode;
#ifdef DEBUG_SERIAL
    Serial.print(F("<handleMenuNext()> Event: change mode"));
    if (mode == MODE_MAIN)
      Serial.println(F("--> MAIN"));
    else if (mode == MODE_CALIB)
      Serial.println(F("--> CALIBRATION"));
    else if (mode == MODE_INTERVAL)
      Serial.println(F("--> INTERVAL"));
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
  Serial.print(F("##### Welcome to Moistensor (protocol v"));
  Serial.print(PROTOCOL_VERSION);
  Serial.println(F(")! #####"));
#endif
#ifdef RESET_EEPROM_CALIBRATION
    EEPROM.put(EEPROM_IDX_THRESHOLD_DRY, 0);
    EEPROM.put(EEPROM_IDX_THRESHOLD_WET, 0);
    EEPROM.put(EEPROM_IDX_INTERVAL_DURATION_IDX, 0);
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
  Serial.println(F("<setup()> change mode --> MAIN"));
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
  uint8_t cursor;
  for (uint8_t i = 0; i < len; ++i) {
    cursor += 1 + (uint8_t)ceil(log((float)i)) + 1 + 8 + 1 + 2 + 1 + 1;
    if (cursor > SERIAL_MONITOR_WIDTH) {
      cursor = 0;
      Serial.println();
    }
    Serial.print(F("["));
    Serial.print(i);
    Serial.print(F("]"));
    for (uint8_t k = 0, mask = 0x80; k < 8; ++k) {
      Serial.print((bool)(buf[i] & mask));
      mask >>= 1;
    }
    Serial.print(F("("));
    if (buf[i] < 16)
      Serial.print(F("0"));
    Serial.print(buf[i], HEX);
    Serial.print(F(") "));
  }
  Serial.println();
}
#endif