#include <EncButton.h>
#include <TimerLED.h>
#include <TinyRF_TX.h> // add ../TinyRF to the list of include paths for this to work
#include <avr/sleep.h>
#include <EEPROM.h>

#define DEBUG_SERIAL

//const int PIN_TX = 12; // hardcoded in tinyrf
const uint8_t PIN_LED = 13;
const uint8_t PIN_BTN = 3; // should be an interrupt pin (D2/D3 for Uno/Nano/ProMini)
const uint8_t PIN_SENSOR = A2;

EncButton<EB_TICK, PIN_BTN> btn;
TimerLED timerLed(PIN_LED, true, false);

#define MODE_MAIN     0
#define MODE_CALIB    1
#define MODE_INTERVAL 2

const uint16_t    MODE_LED[] = {750, 250, 250, 250, 250, 250, 250, 250};
const uint8_t     MODE_LED_MAIN_LEN = 4;
const uint8_t     MODE_LED_CALIB_LEN = 6;
const uint8_t     MODE_LED_INTERVAL_LEN = 8;

const uint16_t    MODE_INTERNAL_LED[] = {250, 250, 250, 250, 250, 250, 250, 250, 250, 250};
const uint16_t    MODE_INTERNAL_DURATIONS[] = {1, 15, 60, 240, 1440}; // in minutes

const uint16_t*   MODE_CALIBRATION_LED = MODE_INTERNAL_LED;

#define EEPROM_IDX_THRESHOLD_DRY  5
#define EEPROM_IDX_THRESHOLD_WET  6



uint8_t mode = MODE_MAIN;
uint8_t intervalDurationIdx = 2;
uint8_t sensorThresholdDry = 200;
uint8_t sensorThresholdWet = 150;

uint8_t sensorLastMeasurement = 0;

void menuTick();
void loadFromEEPROM();

void setup() {
#ifdef DEBUG_SERIAL
  Serial.begin(115200);
  Serial.println(F("Welcome to Remote Moisture Sensing deivce!"));
#endif

  setupTransmitter();
  pinMode(PIN_LED, OUTPUT);

  loadFromEEPROM();

#ifdef DEBUG_SERIAL
  Serial.println(F("> mode: MAIN"));
#endif
}

void loop() {
  btn.tick();
  timerLed.tick();
  menuTick();

//  if (btn.click()) {
//    digitalWrite(PIN_LED, HIGH);
//    const char* msg = "Hello from far away!";
//    send((byte*)msg, strlen(msg), 4);
//    delay(5);
//    digitalWrite(PIN_LED, LOW);
//  }
}

void loadFromEEPROM() {
  sensorThresholdDry = EEPROM.read(EEPROM_IDX_THRESHOLD_DRY);
  sensorThresholdWet = EEPROM.read(EEPROM_IDX_THRESHOLD_WET);
#ifdef DEBUG_SERIAL
  Serial.print(F("loadFromEEPROM(): dry = "));
  Serial.print(sensorThresholdDry);
  Serial.print(F("; wet = "));
  Serial.println(sensorThresholdWet);
#endif
}

void makeMeasurement() {
  sensorLastMeasurement = map(analogRead(PIN_SENSOR), 0, 1023, 0, 255);
#ifdef DEBUG_SERIAL
  Serial.print(F("makeMeasurement(): "));
  Serial.println(sensorLastMeasurement);
#endif
}

void handleMenuCalibration() {
    if (btn.hasClicks()) {
      if (btn.clicks > 1 && btn.clicks < 4) {
        timerLed.setIntervals(btn.clicks * 2, MODE_INTERNAL_LED);
        timerLed.restart();
        makeMeasurement();
        if (btn.clicks == 2) {
          sensorThresholdDry = sensorLastMeasurement;
          EEPROM.write(EEPROM_IDX_THRESHOLD_DRY, sensorThresholdDry);
#ifdef DEBUG_SERIAL
  Serial.print(F("dry value updated: "));
#endif
        }
        else {
          sensorThresholdWet = sensorLastMeasurement;
          EEPROM.write(EEPROM_IDX_THRESHOLD_WET, sensorThresholdWet);
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
      }
    }
}

void handleMenuInterval() {
    if (btn.hasClicks() && btn.clicks < 6) {
      timerLed.setIntervals(btn.clicks * 2, MODE_INTERNAL_LED);
      timerLed.restart();
      intervalDurationIdx = btn.clicks - 1;
#ifdef DEBUG_SERIAL
  Serial.print(F("new interval (in minutes): "));
  Serial.println((uint16_t)MODE_INTERNAL_DURATIONS[intervalDurationIdx]);
#endif
    }
}

void handleMenuNext(const uint8_t nextMode, const uint8_t len, const uint16_t* intervals) {
  if (btn.held()) {
    timerLed.setIntervals(len, intervals);
    timerLed.restart();
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
}
void menuTick() {
  // Main mode: wake up, get measurement, send measurement, sleep
  if (mode == MODE_MAIN) {
    handleMenuNext(MODE_CALIB, MODE_LED_CALIB_LEN, MODE_LED);
    if (btn.click()) {
      // Send current data once
    }
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