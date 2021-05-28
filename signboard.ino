/*
 * First: 1,0,24,25,19,18,14,15,17,16,22,23,20,21,26,27
 * Second: 10,12,11,13,6,9,32,8,7
 * Third: 37, 36, 35, 34, 39, 38, 28, 31, 30
 * Using: 10, 12, (11, 13, 6, 9, 32)
 * 
 * ********** Header format **********
 * 0: Num frames (high)
 * 1: Num frames (low)
 * 2: Frame size (high)
 * 3: Frame size (low)
 *   Repeat for all colors:
 * a: Red value
 * b: Green value
 * c: Blue value
 * 
 * ********** Frame format **********
 * 0: Display time (high)
 * 1: Display time (low)
 * Each pixel is then expressed as a 4-bit code referencing the header. Each byte consists of two pixels.
 * 
 * ********** Error codes ********** (R=red, G=green)
 * G  = awaiting data
 * R  = Timeout for header
 * RR = Timeout for data
 * 
 * ********** Interrupt frame **********
 * The interrupt frame can be transmitted in place of a frame. The interrupt frame consists of 3 bytes of 0xFF and one data byte.
 * 0: Clear screen
 */

#include "FastLED.h"

#define SIZE_SMALL

#ifdef SIZE_SMALL
#define NUM_LEDS_PER_STRIP 160
#define NUM_STRIPS 2
#define LENGTH 300
#endif

#ifdef SIZE_LARGE
#define NUM_LEDS_PER_STRIP 300
#define NUM_STRIPS 7
#endif

// Set to DEBUG to enable debugging over Serial1 and pins 13/14
// #define DEBUG

unsigned long sent;

// current color when loading header
unsigned int x = 0;
byte currByte;
unsigned int displaytime = 0;
unsigned long start_display;

byte r;
byte g;
byte b;

bool headerLoaded = false;
unsigned int numFrames = 0;
unsigned int currFrame = 0;
unsigned int frameSize;
bool nfLoaded = false;
bool dtLoaded = false;

byte int_cmd;

CRGB leds[NUM_LEDS_PER_STRIP * NUM_STRIPS];

CRGB header[16];



void setup() {
  // put your setup code here, to run once:
  Serial.begin(4000000);
  Serial1.begin(1000000);
  //Serial.print("reset");
  pinMode(13, OUTPUT);
  pinMode(14, OUTPUT);
  digitalWrite(13, HIGH);
  delay(1000);
  digitalWrite(13, LOW);
  while (Serial.available()) Serial.read();
  
  FastLED.addLeds<NUM_STRIPS, WS2812, 10, GRB>(leds, NUM_LEDS_PER_STRIP);
  leds[0] = CRGB(0, 255, 0);
  FastLED.show();
  delay(200);
}



void interruptFrame(byte int_cmd) {
  // Interrupt frame received
  headerLoaded = false;
  nfLoaded = false;
  currFrame = 0;
  numFrames = 0;
  displaytime = 0;
  x = 0;
  frameSize = 0;
  if (int_cmd == 0) {
    for (unsigned int x = 2; x < NUM_STRIPS*NUM_LEDS_PER_STRIP; x++) {
      leds[x] = CRGB(0, 0, 0);
    }
    FastLED.show();
  }
}

void waitAvailable() {
  unsigned long _sent=millis();
  while(!Serial.available()) {                    // If you have waited for more than 1s, try again
      if (millis() - _sent > 1000) {
        //digitalWrite(13, HIGH);
        //delay(5000);
        return;
      }
      
    };
}


void loop() {
  // REQUEST THE HEADER
  if (!headerLoaded) {
    while (Serial.available()) Serial.read();       // Empty the serial buffer
    Serial.print("H");                              // Request the header
    sent = millis();


    //digitalWrite(13, HIGH);
    while(!Serial.available()) {                    // If you have waited for more than 1s, try again
      if (millis() - sent > 1000) {
        //digitalWrite(13, HIGH);
        for (unsigned int z = 1; z < NUM_STRIPS*NUM_LEDS_PER_STRIP; z++) {
          leds[x] = CRGB(0, 0, 0);
        }
        leds[0]=CRGB(255, 0, 0);
        digitalWrite(13, HIGH);
        delayMicroseconds(20);
        digitalWrite(13, LOW);
        delayMicroseconds(60);
        digitalWrite(13, HIGH);
        FastLED.show();
        digitalWrite(13, LOW);
        return;
      }
      
    };

    sent = millis();
    while(Serial.available()) {
      // 2: number of frames; 2: frame size
      if (millis() - sent >= 1000) break;
      if (!nfLoaded && Serial.available() >= 4) {
        numFrames = Serial.read()<<8;
        numFrames += Serial.read();
        frameSize = Serial.read()<<8;
        frameSize += Serial.read();
        if ((numFrames == 65535) && ((frameSize >>8) == 255)) {
          interruptFrame(frameSize);     // Interrupt frame received
          return;
        }
        if (frameSize >= LENGTH) frameSize = LENGTH;
        else nfLoaded = true;
      }
      if (nfLoaded && Serial.available() >= 3) {
        r=Serial.read(); g=Serial.read(); b=Serial.read();
        header[x] = CRGB(r, g, b);
        x++;
      }
    }
    while (Serial.available()) Serial.read();
    if (x) {
      headerLoaded = true;
      dtLoaded = false;
      x = 0;
    }
  } 

/* @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
 * RECEIVE FRAME DATA
 * @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
 */
  
  else {
    while (Serial.available()) Serial.read();
    // Request a frame and display it
    Serial.print("F");
    sent = millis();

  
    while(!Serial.available()) {
      if (millis() - sent > 1000) {
        for (unsigned int z = 2; z < NUM_STRIPS*NUM_LEDS_PER_STRIP; z++) {
          leds[z] = CRGB(0, 0, 0);
        }
        leds[0] = CRGB(255, 0, 0);
        leds[1] = CRGB(255, 0, 0);
        digitalWrite(13, HIGH);
        delayMicroseconds(20);
        digitalWrite(13, LOW);
        delayMicroseconds(40);
        digitalWrite(13, HIGH);
        FastLED.show();
        digitalWrite(13, LOW);
        return;
      }
    };
    sent = millis();
    x=0;
    while (Serial.available() < 2);
    displaytime = (Serial.read()<<8) + Serial.read();
    //Serial.println(displaytime);
    dtLoaded = true;
    while(Serial.available() && displaytime) {
        if (millis()-sent > 1000) break;
        dtLoaded = true;
        currByte = Serial.read();
        //if (!displaytime) {Serial.print("UN0DT"); Serial.print(displaytime);}
        //Serial.write(currByte);
        if (currByte==255 && displaytime==65535L) {
          interruptFrame(Serial.read());
          return;
        }
        leds[x] = header[((currByte>>4)&15) - 1];     // Upper nibble comes first
        x++; if (x >= frameSize) break;
        leds[x] = header[((currByte)&15) - 1];
        x++; if (x >= frameSize) break;
    }
    if (x == 0) {
      headerLoaded = false;
      nfLoaded = false;
      currFrame = 0;  
      return;
    }
    //while (Serial.available()) Serial.read();

    /*Serial.print("dck");
    Serial.print(displaytime);
    Serial.print(",");
    Serial.print(numFrames);
    Serial.print(",");
    Serial.print(frameSize);
    Serial.write('\n');*/

    start_display = millis();
    digitalWrite(13, HIGH);
    delayMicroseconds(20);
    digitalWrite(13, LOW);
    delayMicroseconds(20);
    digitalWrite(13, HIGH);
    FastLED.show();
    digitalWrite(13, LOW);
    // This prevents issues when millis() rolls over
    if (start_display >= 4294967295 - displaytime) delay(displaytime);
    else {
      while ((unsigned long)(millis() - start_display) < displaytime);
    }
    //delay(displaytime);

    //Serial.print("rst(dt,dl,x)");
    displaytime = 0;
    //Serial.print("undt");
    dtLoaded = false;
    x = 0;
    currFrame++;
    if (currFrame >= numFrames) {
      //Serial.print("rst(hl,nl,cf)");
      headerLoaded = false;
      nfLoaded = false;
      currFrame = 0;      
    }

#ifdef DEBUG
    digitalWrite(14, LOW);
#endif
  }
  
}
