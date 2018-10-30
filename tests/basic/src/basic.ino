#include "ArduinoFactoryBridge.h"

ArduinoFactoryBridge bridge("test");

int counter = 0;
float divider = 2000.0;
String test_string1 = "";
String test_string2 = "";

void setup()
{
    bridge.begin();
    bridge.writeHello();
    bridge.setInitData("s", "hi!");
    bridge.writeReady();
}

void loop()
{
    if (!bridge.isPaused()) {
        bridge.write("numbers", "df", counter, divider);
        bridge.write("strings", "ss", test_string1.c_str(), test_string2.c_str());
        counter++;
        divider /= 3.0;
        test_string1 += "s";
        test_string2 += "b";
        delay(10);
    }

    if (bridge.available()) {
        int status = bridge.read();
        if (status == 0) {
            String command = bridge.getCommand();
            if (command.equals("d")) {
                counter = 0;
            }
            else if (command.equals("f")) {
                divider = 2000;
            }
            else if (command.equals("s1")) {
                test_string1 = "";
            }
            else if (command.equals("s2")) {
                test_string2 = "";
            }
        }
    }
}
