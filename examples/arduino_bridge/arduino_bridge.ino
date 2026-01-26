#include <Adafruit_NeoPixel.h>

#define PIN        3        // Arduino Pin connected to Data In of LED strip
#define NUMPIXELS  64       // Number of LEDs
#define BAUDRATE   115200   // specific baud rate matching the Pi script

// Initialize NeoPixel strip
Adafruit_NeoPixel pixels(NUMPIXELS, PIN, NEO_GRB + NEO_KHZ800);

void setup() {
  Serial.begin(BAUDRATE); // Start serial communication
  pixels.begin();         // Initialize NeoPixel library
  pixels.setBrightness(50); // Set brightness (0-255)
  pixels.show();          // Initialize all pixels to 'off'
}

void loop() {
  if (Serial.available() > 0) {
    char cmd = Serial.read();

    if (cmd == 's') { // 's' for Set Color (Solid)
      waitForBytes(3); // Wait for R, G, B values
      uint8_t r = Serial.read();
      uint8_t g = Serial.read();
      uint8_t b = Serial.read();
      
      setSolidColor(pixels.Color(r, g, b));
    }
  }
}

// Helper to wait for N bytes available on Serial
void waitForBytes(int n) {
  while (Serial.available() < n) {
    delay(1);
  }
}

// Function to set all pixels to a color
void setSolidColor(uint32_t c) {
  for(int i=0; i<NUMPIXELS; i++) {
    pixels.setPixelColor(i, c);
  }
  pixels.show();
}
