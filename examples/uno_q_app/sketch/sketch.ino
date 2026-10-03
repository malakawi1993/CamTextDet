// Text Spotter - the microcontroller side of the UNO Q.
// Python reads the text and calls these functions over the Bridge.

#include <Arduino_RouterBridge.h>
#include <Arduino_LED_Matrix.h>
#include <vector>

Arduino_LED_Matrix matrix;

const uint8_t FRAME_SIZE = 8 * 13;  // the LED matrix has 8 rows and 13 columns
uint8_t frame[FRAME_SIZE] = {0};

// Python calls this with the text the camera sees.
void show_text(String text) {
    Monitor.print("Camera sees: ");
    Monitor.println(text);
}

// Python calls this with a new picture for the LED matrix.
void draw(std::vector<uint8_t> newFrame) {
    size_t len = min(newFrame.size(), (size_t)FRAME_SIZE);
    memcpy(frame, newFrame.data(), len);
}

void setup() {
    Monitor.begin(115200);

    matrix.begin();
    matrix.setGrayscaleBits(3);  // brightness from 0 to 7
    matrix.clear();

    Bridge.begin();
    Bridge.provide("show_text", show_text);
    Bridge.provide("draw", draw);
}

void loop() {
    matrix.draw(frame);  // keep showing the newest picture
    delay(10);
}
