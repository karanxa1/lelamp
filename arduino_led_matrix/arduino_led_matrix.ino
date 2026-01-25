#include <Adafruit_NeoPixel.h>

#define LED_PIN 6
#define LED_COUNT 64
#define TIMEOUT 5000   // 5 seconds timeout to white

Adafruit_NeoPixel matrix(LED_COUNT, LED_PIN, NEO_GRB + NEO_KHZ800);

String input = "";
unsigned long lastCommandTime = 0;
bool isWhite = false;

void setup() {
  Serial.begin(115200); // Higher baud rate for smoother updates
  matrix.begin();
  matrix.setBrightness(80); // Moderate brightness
  
  setWhite();  // Default on startup
}

void processCommand(String cmd) {
  // Format: "R255G000B000" for SOLID color
  if (cmd.startsWith("R")) {
    int r = cmd.substring(cmd.indexOf('R')+1, cmd.indexOf('G')).toInt();
    int g = cmd.substring(cmd.indexOf('G')+1, cmd.indexOf('B')).toInt();
    int b = cmd.substring(cmd.indexOf('B')+1).toInt();
  
    for (int i = 0; i < LED_COUNT; i++) {
        matrix.setPixelColor(i, matrix.Color(r, g, b));
    }
    matrix.show();
  }
}

void loop() {
  // Check for serial data
  while (Serial.available()) {
    char c = Serial.peek(); // Peek first

    // BINARY COMMANDS (Lower case specific markers)
    if (c == 'p') {
       Serial.read(); // Consume 'p'
       // Expect 192 bytes (64 * 3)
       uint8_t buffer[192];
       int bytesRead = Serial.readBytes(buffer, 192);
       if (bytesRead == 192) {
         for(int i=0; i<LED_COUNT; i++) {
           matrix.setPixelColor(i, matrix.Color(buffer[i*3], buffer[i*3+1], buffer[i*3+2]));
         }
         matrix.show();
         lastCommandTime = millis();
         isWhite = false;
         input = ""; // Clear any partial text
       }
       continue;
    }
    
    // TEXT COMMANDS
    c = Serial.read(); // Consume
    if (c == '\n') {
      processCommand(input);
      input = "";
      lastCommandTime = millis();  // Reset timer
      isWhite = false;
    } else {
      input += c;
    }
  }

  // If timeout reached -> set white
  if (!isWhite && (millis() - lastCommandTime > TIMEOUT)) {
    setWhite();
  }
}

void setWhite() {
  for (int i = 0; i < LED_COUNT; i++) {
    matrix.setPixelColor(i, matrix.Color(255, 255, 255));
  }
  matrix.show();
  isWhite = true;
}
