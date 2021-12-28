#include <EncButton.h>
#include <TimerLED.h>
#include <TimerMs.h>
#include <TinyRF_TX.h> // add ../TinyRF to the list of include paths for this to work
#include <GyverPower.h>
#include <EEPROM.h>

#define DEBUG_SERIAL

//const int PIN_TX = 12; // hardcoded in tinyrf
const uint8_t PIN_LED = 13;
const uint8_t PIN_BTN = 3; // should be an interrupt pin (D2/D3 for Uno/Nano/ProMini)
const uint8_t BTN_INTERRUPT = 1; // 0 if D2, 1 if D3
const uint8_t PIN_SENSOR = A2;

EncButton<EB_TICK, PIN_BTN> btn;
TimerLED timerLed(PIN_LED, true, false);
TimerMs timerIdleToSleep(5000, 0, 1);

#define MODE_MAIN     0
#define MODE_CALIB    1
#define MODE_INTERVAL 2

const uint16_t    MODE_LED[] = {750, 250, 250, 250, 250, 250, 250, 250};
const uint8_t     MODE_LED_MAIN_LEN = 4;
const uint8_t     MODE_LED_CALIB_LEN = 6;
const uint8_t     MODE_LED_INTERVAL_LEN = 8;

const uint16_t    MODE_INTERNAL_LED[] = {250, 250, 250, 250, 250, 250, 250, 250, 250, 250};
const uint16_t    MODE_INTERNAL_DURATIONS[] = {1, 15, 60, 240, 1440}; // in minutes
const uint8_t     MODE_INTERNAL_DURATIONS_LEN = 5;

const uint16_t*   MODE_CALIBRATION_LED = MODE_INTERNAL_LED;

const uint16_t    GOSLEEP_LED[] = {20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20};
const uint8_t     GOSLEEP_LED_LEN = 20;

#define EEPROM_IDX_THRESHOLD_DRY          5
#define EEPROM_IDX_THRESHOLD_WET          6
#define EEPROM_IDX_INTERVAL_DURATION_IDX  7



uint8_t mode = MODE_MAIN;
uint8_t intervalDurationIdx = 2;
uint8_t sensorThresholdDry = 200;
uint8_t sensorThresholdWet = 150;
uint8_t sensorLastMeasurement = 0;

bool isSleeping = false;


void handleWakeUp() {
  if (!isSleeping)
    return;
  detachInterrupt(BTN_INTERRUPT);
#ifdef DEBUG_SERIAL
  Serial.println("Interrupt Fired!");
#endif
  power.wakeUp();
  isSleeping = false;
  timerIdleToSleep.restart();
}

void prepareForSleep() {
  btn.resetState();
  timerLed.stop();
  timerIdleToSleep.stop();
  isSleeping = true;
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
  if (_wet < _dry) {
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
  if (_interval < MODE_INTERNAL_DURATIONS_LEN) {
    intervalDurationIdx = _interval;
#ifdef DEBUG_SERIAL
  Serial.print(F(" interval = "));
  Serial.println(MODE_INTERNAL_DURATIONS[intervalDurationIdx]);
#endif
  } else {
#ifdef DEBUG_SERIAL
  Serial.println();
  Serial.print(F("loadFromEEPROM() WARNING: validation failed - [idx] interval = ["));
  Serial.print(intervalDurationIdx);
  Serial.print(F("] "));
  Serial.println(MODE_INTERNAL_DURATIONS[intervalDurationIdx]);
#endif
  }
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
    if (btn.hasClicks() && btn.clicks <= MODE_INTERNAL_DURATIONS_LEN) {
      timerLed.setIntervals(btn.clicks * 2, MODE_INTERNAL_LED);
      timerLed.restart();
      intervalDurationIdx = btn.clicks - 1;
      EEPROM.write(EEPROM_IDX_INTERVAL_DURATION_IDX, intervalDurationIdx);
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
    // Stop goToSleep timer if not in mode MAIN
    if (mode != MODE_MAIN) {
      timerIdleToSleep.stop();
    }
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



/////////////////////////////////////////////////////////////////////////
///////////////////////////////// SETUP /////////////////////////////////
/////////////////////////////////////////////////////////////////////////
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

  // Setup sleeping stuff
  power.autoCalibrate(); // автоматическая калибровка
  power.setSleepMode(POWERDOWN_SLEEP);

  timerIdleToSleep.attach([]() -> void {
#ifdef DEBUG_SERIAL
  Serial.println("Going to sleep!");
#endif
      // flash with led
      for (uint8_t i = 0; i < GOSLEEP_LED_LEN; ++i) {
        digitalWrite(PIN_LED, i % 2 ? HIGH : LOW);
        delay(GOSLEEP_LED[i]);
      }
      digitalWrite(PIN_LED, LOW);
      
      prepareForSleep();
      attachInterrupt(BTN_INTERRUPT, handleWakeUp, LOW);
      power.sleepDelay(MODE_INTERNAL_DURATIONS[intervalDurationIdx] * 60000);

#ifdef DEBUG_SERIAL
  Serial.println("Just woke up!");
#endif
  });
  timerIdleToSleep.restart();
}


/////////////////////////////////////////////////////////////////////////
////////////////////////////////// LOOP /////////////////////////////////
/////////////////////////////////////////////////////////////////////////
void loop() {
  btn.tick();
  timerLed.tick();
  timerIdleToSleep.tick();

  // Main mode: wake up, get measurement, send measurement, sleep
  if (mode == MODE_MAIN) {
    handleMenuNext(MODE_CALIB, MODE_LED_CALIB_LEN, MODE_LED);
    // Update goToSleepTimer every time btn is down in mode MAIN
    if (btn.state()) {
      timerIdleToSleep.restart();
    }
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

//  if (btn.click()) {
//    digitalWrite(PIN_LED, HIGH);
//    const char* msg = "Hello from far away!";
//    send((byte*)msg, strlen(msg), 4);
//    delay(5);
//    digitalWrite(PIN_LED, LOW);
//  }
}