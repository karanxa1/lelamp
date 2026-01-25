#include <Adafruit_NeoPixel.h>

#define PIN        3
#define NUMPIXELS  64
#define BAUDRATE   115200

Adafruit_NeoPixel pixels(NUMPIXELS, PIN, NEO_GRB + NEO_KHZ800);

bool connected = false;

void setup() {
  Serial.begin(BAUDRATE);
  pixels.begin();
  pixels.setBrightness(32); // Safe brightness
  pixels.show(); 
  
  // Debug blink
  pinMode(13, OUTPUT);
  digitalWrite(13, HIGH); delay(100); digitalWrite(13, LOW);
}

void loop() {
  // If we haven't received any command yet, play default animation
  if (!connected) {
    rainbowCycle(10); // Check for serial inside this function
  } else {
    // Normal Serial processing
    if (Serial.available() > 0) {
      handleSerial();
    }
  }
}

void handleSerial() {
    char cmd = Serial.read();
    digitalWrite(13, HIGH); // Debug LED

    if (cmd == 'p') { // Paint
      uint8_t buffer[NUMPIXELS * 3];
      int count = 0;
      unsigned long start = millis();
      while(count < NUMPIXELS * 3 && (millis() - start < 200)) { 
         if(Serial.available()) buffer[count++] = Serial.read();
      }
      if (count == NUMPIXELS * 3) {
         for(int i=0; i<NUMPIXELS; i++) {
           pixels.setPixelColor(i, pixels.Color(buffer[i*3], buffer[i*3+1], buffer[i*3+2]));
         }
         pixels.show();
      }
    }
    else if (cmd == 's') { // Solid
       uint8_t buf[3];
       int c = 0;
       unsigned long start = millis();
       while(c < 3 && (millis() - start < 100)) {
          if (Serial.available()) buf[c++] = Serial.read();
       }
       if (c == 3) {
           uint32_t color = pixels.Color(buf[0], buf[1], buf[2]);
           for(int i=0; i<NUMPIXELS; i++) {
             pixels.setPixelColor(i, color);
           }
           pixels.show();
       }
    }
    else if (cmd == 'c') { // Clear
      pixels.clear();
      pixels.show();
    }
    else if (cmd == 'r') { // Reset logic
      connected = false;
    }

    digitalWrite(13, LOW);
}

// Return true if serial interrupted, false otherwise
void rainbowCycle(uint8_t wait) {
  uint16_t i, j;

  for(j=0; j<256; j++) { // 1 cycle of all colors on wheel
    for(i=0; i< pixels.numPixels(); i++) {
        // CHECK FOR SERIAL INTERRUPT
        if (Serial.available() > 0) {
            connected = true;
            handleSerial(); // Handle the first byte immediately
            return;
        }
      pixels.setPixelColor(i, Wheel(((i * 256 / pixels.numPixels()) + j) & 255));
    }
    pixels.show();
    delay(wait);
  }
}

// Input a value 0 to 255 to get a color value.
// The colours are a transition r - g - b - back to r.
uint32_t Wheel(byte WheelPos) {
  WheelPos = 255 - WheelPos;
  if(WheelPos < 85) {
    return pixels.Color(255 - WheelPos * 3, 0, WheelPos * 3);
  }
  if(WheelPos < 170) {
    WheelPos -= 85;
    return pixels.Color(0, WheelPos * 3, 255 - WheelPos * 3);
  }
  WheelPos -= 170;
  return pixels.Color(WheelPos * 3, 255 - WheelPos * 3, 0);
}
