#include "src/TinyRF/TinyRF_RX.h" // add ../TinyRF to the list of include paths for this to work

#define SERIAL
#define DEBUG

int     rxPin      = 2;   // The number of signal from the Rx
int     ledPin     = 13;  // The number of the onboard LED pin

void hexBinDump(const uint8_t*, const uint8_t&);

void setup() {
  Serial.begin(115200);
  setupReceiver(rxPin);
  pinMode(ledPin, OUTPUT);
}

void loop() {
  const uint8_t bufSize = 6;
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
    // DEVICE_ID        5 bits  (0 .. 31)
    // prot_version     3 bits  (0 .. 7)
    // packet_type      3 bits  (0 .. 7)
    //
    // packet_type == 1: sensor measurement
    // voltage          3 bits  (0 .. 7)      0 - unknown
    // unit             2 bits  (0 .. 3)      0 - seconds, 1 - minutes, 2 - hours, 3 - days
    // timestamp        10 bits (0 .. 1023)   time since device started in units
    // |       b0             |  |           b1           | |     b2      | |      b3      |
    // x x x x x  x     x     x  x    x    x   x  x  x x  x x x x x x x x x x x  x x x x x x
    // DEVICE_ID  prot_version   packet_type   voltage unit timestamp_in_s/m/h/d  sensor_val 
    //
    // packet_type == 2: share calibration data
    // voltage          3 bits  (0 .. 7)      0 - unknown
    // unit             2 bits  (0 .. 3)      0 - seconds, 1 - minutes, 2 - hours, 3 - days
    // timestamp        10 bits (0 .. 1023)   time since device started in units
    // |       b0             |  |           b1           | |     b2      | |      b3      |
    // x x x x x  x     x     x  x    x    x   x  x  x x  x x x x x x x x x x x  x x x x x x
    // DEVICE_ID  prot_version   packet_type   voltage unit timestamp_in_s/m/h/d  sensor_val  

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
      if (packetType == 1) { // sensor measurement
        if (numRcvdBytes != 4) {
          Serial.print(F("[PRv1-1] Invalid packet: Received "));
          Serial.print(numRcvdBytes);
          Serial.println(F(" bytes (expected 4)"));
          return;
        }
        uint8_t voltage = b1 >> 2 & 0b111;
        uint8_t unitTime = b1 & 0b11;
        uint8_t b2 = buf[2],
                b3 = buf[3];
        uint16_t timeStamp = b2 << 2 | (b3 >> 6 & 0b11);
        uint8_t measurement = b3 & 0b111111;

        Serial.print(F("[PRv1-1] Voltage: "));
        if (voltage) Serial.print(voltage);
        else Serial.print(F("unknown"));
        Serial.print(F(" Timestamp: "));
        Serial.print(timeStamp);
        Serial.print(((const char*[]){"s", "m", "h", "d"})[unitTime]);
        Serial.print(F(" Measurement: "));
        Serial.println(measurement);
        return;
      } else {
        Serial.println(F("[PR] unsupported protocol version"));
        return;
      }
    } else {
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