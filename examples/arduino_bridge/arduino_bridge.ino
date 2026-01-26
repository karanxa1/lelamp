#include <Adafruit_NeoPixel.h>

#define PIN        3        
#define NUMPIXELS  64       
#define BAUDRATE   115200   

Adafruit_NeoPixel pixels(NUMPIXELS, PIN, NEO_GRB + NEO_KHZ800);

void setup() {
  Serial.begin(BAUDRATE);
  pixels.begin();         
  pixels.setBrightness(50); 
  pixels.show();          

  // Startup Flash - Then stay ON (Dim White)
  for(int i=0; i<NUMPIXELS; i++) {
     pixels.setPixelColor(i, pixels.Color(20, 20, 20)); // Dim White
  }
  pixels.show();

  // HANDSHAKE: Tell Python we are ready
  Serial.println("READY");
}

void loop() {
  if (Serial.available() > 0) {
    char cmd = Serial.read();

    if (cmd == 's') { // Set Solid Color
      // Wait safely for 3 bytes
      unsigned long start = millis();
      while(Serial.available() < 3) {
         if(millis() - start > 500) break; // Timeout
      }
      
      if(Serial.available() >= 3) {
        uint8_t r = Serial.read();
        uint8_t g = Serial.read();
        uint8_t b = Serial.read();
        setSolidColor(pixels.Color(r, g, b));
      }
    }
    else if (cmd == 'p') { // Paint Frame
      int expected = NUMPIXELS * 3;
      int count = 0;
      unsigned long start = millis();
      
      // Temporary buffer for RGB triplet
      uint8_t rgb[3]; 

      while(count < expected) {
         if(Serial.available()) {
            // Read 3 bytes at a time for each pixel? 
            // No, just read byte by byte to be robust
            int pixelIdx = count / 3;
            int channel = count % 3;
            rgb[channel] = Serial.read();
            
            if (channel == 2) { // We have R,G,B for this pixel
                pixels.setPixelColor(pixelIdx, pixels.Color(rgb[0], rgb[1], rgb[2]));
            }
            count++;
         }
         if(millis() - start > 500) break; // Timeout
      }
      pixels.show(); 
    }
  }
}

void setSolidColor(uint32_t c) {
  for(int i=0; i<NUMPIXELS; i++) {
    pixels.setPixelColor(i, c);
  }
  pixels.show();
}
