#include "src/TinyRF/TinyRF_RX.h" // add ../TinyRF to the list of include paths for this to work

#define SERIAL
#define DEBUG

int     rxPin      = 2;         // The number of signal from the Rx
int     ledPin     = 13;        // The number of the onboard LED pin

#define PRV1_PTYPEMT 1          // Measurement
#define PRV1_PTYPEMT_SIZE 5

#define PRV1_PTYPECLBR 2        // Calibration
#define PRV1_PTYPECLBR_SIZE 8

void hexBinDump(const uint8_t*, const uint8_t&);

void setup() {
  Serial.begin(115200);
  setupReceiver(rxPin);
  pinMode(ledPin, OUTPUT);
}

void loop() {
  const uint8_t bufSize = max(PRV1_PTYPEMT_SIZE, PRV1_PTYPECLBR_SIZE);
  byte buf[bufSize];
  uint8_t numLostMsgs = 0;
  uint8_t numRcvdBytes = 0;

  uint8_t err = getReceivedData(buf, bufSize, numRcvdBytes, numLostMsgs);

  if (err == TRF_ERR_NO_DATA) {
    return;
  }
  
  if (err == TRF_ERR_BUFFER_OVERFLOW) {
    Serial.println(F("[RF] Buffer too small for received data!"));
    return;
  }
  
  if (err == TRF_ERR_CORRUPTED) {
    Serial.println(F("[RF] Received corrupted data."));
    return;
  }

  if (err == TRF_ERR_SUCCESS) {
// Protocol v1
// DEVICE_ID        5 bits  (1 .. 31)
// p_ver            3 bits  (0 .. 7)
// ptype            3 bits  (0 .. 7)
//
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
//
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

#ifdef DEBUG
    Serial.print(F("> "));
    hexBinDump(buf, numRcvdBytes);
#endif

    if (numRcvdBytes <= 1) {
      Serial.print(F("[PR] Invalid packet: Received only "));
      Serial.print(numRcvdBytes);
      Serial.println(F(" bytes (expected > 1)"));
      return;
    }

    uint8_t b0 = buf[0];
    uint8_t deviceID = b0 >> 3;
    uint8_t protocolVersion = b0 & 0b111;

    Serial.print(F("DeviceID: "));
    Serial.print((int)deviceID);
    Serial.print(F("\tProtocol_version: "));
    Serial.println((int)protocolVersion);

    uint8_t b1 = buf[1];
    if (protocolVersion == 1) {
      uint8_t packetType = b1 >> 5;
      if (packetType == PRV1_PTYPEMT) { // sensor measurement transmission
        if (numRcvdBytes != PRV1_PTYPEMT_SIZE) {
          Serial.print(F("[PRv1-"));
          Serial.print(PRV1_PTYPEMT);
          Serial.print(F("] Invalid packet: Received "));
          Serial.print(numRcvdBytes);
          Serial.print(F(" bytes (expected "));
          Serial.print(PRV1_PTYPEMT_SIZE);
          Serial.println(F(")"));
          return;
        }
        uint8_t voltage = b1 >> 2 & 0b111;
        uint8_t unitTime = b1 >> 1 & 1;
        uint8_t b2 = buf[2],
                b3 = buf[3],
                b4 = buf[4];
        uint16_t timeStamp = (b1 & 1) << 14 | b2 << 6 | (b3 >> 2 & 0b111111);
        uint16_t measurement = (b3 & 0b11) << 8 | b4;

        Serial.print(F("[PRv1-"));
        Serial.print(PRV1_PTYPEMT);
        Serial.print(F("] Voltage: "));
        if (voltage) Serial.print(voltage);
        else Serial.print(F("unknown"));
        Serial.print(F(" Timestamp: "));
        Serial.print(timeStamp);
        Serial.print(unitTime ? F("h") : F("m"));
        Serial.print(F(" Measurement*: "));
        Serial.println(measurement);
        return;
      }
      else if (packetType == PRV1_PTYPECLBR) { // calibration data
        if (numRcvdBytes != PRV1_PTYPECLBR_SIZE) {
          Serial.print(F("[PRv1-"));
          Serial.print(PRV1_PTYPECLBR);
          Serial.print(F("] Invalid packet: Received "));
          Serial.print(numRcvdBytes);
          Serial.print(F(" bytes (expected "));
          Serial.print(PRV1_PTYPECLBR_SIZE);
          Serial.println(F(")"));
          return;
        }
        uint8_t voltage = b1 >> 2 & 0b111;
        uint8_t unitTime = b1 >> 1 & 1;
        uint8_t b2 = buf[2],
                b3 = buf[3],
                b4 = buf[4],
                b5 = buf[5],
                b6 = buf[6],
                b7 = buf[7];
        uint16_t timeStamp = (b1 & 1) << 14 | b2 << 6 | (b3 >> 2 & 0b111111);
        uint8_t V_min = (b3 & 0b11) << 1 | b4 >> 7;
        uint8_t V_max = b4 >> 4 & 0b111;
        uint16_t calibrationDry = (b4 & 0b1111) << 6 | (b5 >> 2 & 0b111111);
        uint16_t calibrationWet = (b5 & 0b11) << 8 | b6;
        uint8_t intervalIdx = b7 >> 5 & 0b111;
        const uint16_t MODE_INTERNAL_DURATIONS[] = {1, 15, 60, 240, 1440}; // in minutes
        bool first = b7 >> 4 & 1;

        Serial.print(F("[PRv1-"));
        Serial.print(PRV1_PTYPECLBR);
        Serial.print(F("] Voltage: "));
        if (voltage) Serial.print(voltage);
        else Serial.print(F("unknown"));
        Serial.print(F(" Timestamp: "));
        Serial.print(timeStamp);
        Serial.print(unitTime ? F("h") : F("m"));
        Serial.print(F(" V_min: "));
        if (V_min) Serial.print(V_min);
        else Serial.print(F("unknown"));
        Serial.print(F(" V_max: "));
        if (V_max) Serial.print(V_max);
        else Serial.print(F("unknown"));
        Serial.print(F(" Calibration_dry: "));
        Serial.print(calibrationDry);
        Serial.print(F(" Calibration_wet: "));
        Serial.print(calibrationWet);
        Serial.print(F(" [Idx] Interval: ["));
        Serial.print(intervalIdx);
        Serial.print(F("] "));
        Serial.print(MODE_INTERNAL_DURATIONS[intervalIdx]);
        Serial.print(F(" First: "));
        Serial.println(first ? F("true") : F("false"));
        return;
      }
      else {
        Serial.println(F("[PR] unsupported packet type"));
        return;
      }
    }
    else {
      Serial.println(F("[PR] unsupported protocol version"));
      return;
    }

    if (numLostMsgs > 0) {
      Serial.print(F("[RF] "));
      Serial.print(numLostMsgs);
      Serial.println(F(" messages were lost before this message."));
    }
  }
}


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