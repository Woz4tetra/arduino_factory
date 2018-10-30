#ifndef _ARDUINO_FACTORY_BRIDGE_H_
#define _ARDUINO_FACTORY_BRIDGE_H_


#include <Arduino.h>
#include <TimeLib.h>

#include <ArduinoFactoryBridgeConstants.h>


class ArduinoFactoryBridge {
public:
    ArduinoFactoryBridge(String whoiam);
    void begin();
    bool available();
    int read();
    String getCommand();
    bool isPaused();

    void changeBaud(int newBaud);

    bool unpause();
    bool pause();

    void setInitData(const char *formats, ...);
    void writeHello();
    void writeReady();

    void writeTime();
    void write(String name, const char *formats, ...);
private:
    String _command;
    String _whoiam;
    String _initPacket;
    bool _paused;

    void writeWhoiam();
    void writeInit();

    void printInt64(int64_t value);
    void printUInt64(uint64_t value);

    uint32_t _arduinoPrevTime;
    uint32_t _overflowCount;
    uint64_t _sequence_num;
    char _timePrintBuffer[32];
};

#endif  // _ARDUINO_FACTORY_BRIDGE_H_
