#include <Adafruit_NeoPixel.h>

#define PIN        A1
#define NUMPIXELS  64
#define BAUDRATE   115200

Adafruit_NeoPixel pixels(NUMPIXELS, PIN, NEO_GRB + NEO_KHZ800);

void setup() {
  Serial.begin(BAUDRATE);
  pixels.begin();
  pixels.show(); // Initialize all pixels to 'off'
  
  // Debug toggle to signal startup
  pinMode(13, OUTPUT);
  digitalWrite(13, HIGH);
  delay(100);
  digitalWrite(13, LOW);
  delay(100);
  digitalWrite(13, HIGH);
}

void loop() {
  if (Serial.available() > 0) {
    char cmd = Serial.read();
    
    // Toggle internal LED on any command
    digitalWrite(13, !digitalRead(13)); 

    if (cmd == 'p') { // Paint frame
      // Paint is large, better to read carefully
      // We expect 192 bytes.
      uint8_t buffer[NUMPIXELS * 3];
      int count = 0;
      unsigned long start = millis();
      
      // Increased timeout slightly for paint
      while(count < NUMPIXELS * 3 && (millis() - start < 200)) { 
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
       // Set Brightness global if needed or just color
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
    else if (cmd == 'b') { // Set brightness (optional future proofing)
       unsigned long start = millis();
       while(!Serial.available() && (millis() - start < 100));
       if (Serial.available()) {
         uint8_t b = Serial.read();
         pixels.setBrightness(b);
         pixels.show();
       }
    }
  }
}
