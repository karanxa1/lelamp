#include <Adafruit_NeoPixel.h>

#define PIN        A1
#define NUMPIXELS  64
#define BAUDRATE   115200

Adafruit_NeoPixel pixels(NUMPIXELS, PIN, NEO_GRB + NEO_KHZ800);

void setup() {
  Serial.begin(BAUDRATE);
  pixels.begin();
  pixels.show(); // Initialize all pixels to 'off'
}

void loop() {
  if (Serial.available() > 0) {
    char cmd = Serial.read();
    
    if (cmd == 'p') { // Paint frame
      // Wait for all data (64 LEDs * 3 channels = 192 bytes)
      // Blocking wait might be dangerous if packets drop, but keep it simple for now
      // A small timeout mechanism would be better but keeping it "short"
      uint8_t buffer[NUMPIXELS * 3];
      int count = 0;
      unsigned long start = millis();
      
      while(count < NUMPIXELS * 3 && (millis() - start < 100)) { // 100ms timeout
         if(Serial.available()) {
            buffer[count++] = Serial.read();
         }
      }
      
      if (count == NUMPIXELS * 3) {
         for(int i=0; i<NUMPIXELS; i++) {
           pixels.setPixelColor(i, pixels.Color(buffer[i*3], buffer[i*3+1], buffer[i*3+2]));
         }
         pixels.show();
      }
    }
    else if (cmd == 's') { // Solid color
       unsigned long start = millis();
       uint8_t buf[3];
       int c = 0;
       
       while(c < 3 && (millis() - start < 50)) {
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
  }
}
