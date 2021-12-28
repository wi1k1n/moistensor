#include "src/TinyRF/TinyRF_RX.h"

int     rxPin      = 2;   //The number of signal from the Rx
int     ledPin     = 13;  //The number of the onboard LED pin

void setup() {
  Serial.begin(115200);
  setupReceiver(rxPin);
  pinMode(ledPin, OUTPUT);
}

void loop() {
  const uint8_t bufSize = 30;
  byte buf[bufSize];
  uint8_t numLostMsgs = 0;
  uint8_t numRcvdBytes = 0;

  uint8_t err = getReceivedData(buf, bufSize, numRcvdBytes, numLostMsgs);

  if(err == TRF_ERR_NO_DATA){
    return;
  }
  
  if(err == TRF_ERR_BUFFER_OVERFLOW){
    Serial.println("Buffer too small for received data!");
    return;
  }
  
  if(err == TRF_ERR_CORRUPTED){
    Serial.println("Received corrupted data.");
    return;
  }

  if(err == TRF_ERR_SUCCESS){
    Serial.print("Received: ");
    for(int i=0; i<numRcvdBytes; i++){
      Serial.print((char)buf[i]);
    }
    Serial.println("");

    if(numLostMsgs>0){
      Serial.print(numLostMsgs);
      Serial.println(" messages were lost before this message.");
    }
  }
}