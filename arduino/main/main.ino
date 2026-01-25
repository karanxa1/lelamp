#include <Adafruit_NeoPixel.h>

#define PIN        A1
#define NUMPIXELS  64
#define BAUDRATE   115200

Adafruit_NeoPixel pixels(NUMPIXELS, PIN, NEO_GRB + NEO_KHZ800);

void setup() {
  Serial.begin(BAUDRATE);
  pixels.begin();
  pixels.setBrightness(32); // Safe brightness
  pixels.show(); 
  
  // --- STARTUP SELF-TEST ---
  // This runs automatically on power/reset.
  // If you don't see this, the LED Wiring or Power is WRONG.
  
  // 1. Red
  colorWipe(pixels.Color(255, 0, 0), 10); 
  delay(500);
  
  // 2. Green
  colorWipe(pixels.Color(0, 255, 0), 10);
  delay(500);
  
  // 3. Blue
  colorWipe(pixels.Color(0, 0, 255), 10);
  delay(500);
  
  // 4. Off
  colorWipe(pixels.Color(0, 0, 0), 5);
  // -------------------------
  
  // Signal ready with onboard LED
  pinMode(13, OUTPUT);
  blink(3);
}

void loop() {
  if (Serial.available() > 0) {
    char cmd = Serial.read();
    digitalWrite(13, HIGH); // LED On while processing

    if (cmd == 'p') { // Paint frame
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
    else if (cmd == 's') { // Solid color
       unsigned long start = millis();
       uint8_t buf[3];
       int c = 0;
       
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
    
    digitalWrite(13, LOW); // LED Off
  }
}

// Helper for startup animation
void colorWipe(uint32_t color, int wait) {
  for(int i=0; i<pixels.numPixels(); i++) {
    pixels.setPixelColor(i, color);
    pixels.show();
    delay(wait);
  }
}

void blink(int times) {
  for(int i=0; i<times; i++) {
    digitalWrite(13, HIGH); delay(100);
    digitalWrite(13, LOW); delay(100);
  }
}
