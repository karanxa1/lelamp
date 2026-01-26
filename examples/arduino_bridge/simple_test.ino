#include <Adafruit_NeoPixel.h>

// WHICH PIN IS YOUR DATA WIRE CONNECTED TO?
#define PIN        3 

// HOW MANY PIXELS?
#define NUMPIXELS  64 

Adafruit_NeoPixel pixels(NUMPIXELS, PIN, NEO_GRB + NEO_KHZ800);

void setup() {
  pixels.begin();
  pixels.setBrightness(50);
}

void loop() {
  // RED
  for(int i=0; i<NUMPIXELS; i++) {
    pixels.setPixelColor(i, pixels.Color(255, 0, 0));
  }
  pixels.show();
  delay(1000);

  // GREEN
  for(int i=0; i<NUMPIXELS; i++) {
    pixels.setPixelColor(i, pixels.Color(0, 255, 0));
  }
  pixels.show();
  delay(1000);

  // BLUE
  for(int i=0; i<NUMPIXELS; i++) {
    pixels.setPixelColor(i, pixels.Color(0, 0, 255));
  }
  pixels.show();
  delay(1000);
  
  // OFF
  pixels.clear();
  pixels.show();
  delay(1000);
}
