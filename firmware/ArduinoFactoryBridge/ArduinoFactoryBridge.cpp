
#include <ArduinoFactoryBridge.h>

const unsigned long DEFAULT_TIME = 1357041600; // Jan 1 2013


#define EXTRACT_DATA_FROM_ARGS() \
    va_list args;   \
    va_start(args, formats);    \
    String data = String(formats) + "\t";   \
    while (*formats != '\0') {  \
        if (*formats == 'd') {  \
            int i = va_arg(args, int);  \
            data += String(i);  \
        }   \
        else if (*formats == 's') { \
            char *s = va_arg(args, char*);  \
            data += s;  \
        }   \
        else if (*formats == 'f') { \
            double f = va_arg(args, double);  \
            data += String(f);  \
        }   \
        data += "\t";   \
        ++formats;  \
    }   \
    va_end(args);   \
    data += PACKET_END; \

ArduinoFactoryBridge::ArduinoFactoryBridge(String whoiam)
{
    _command = "";
    _whoiam = whoiam;
    _initPacket = "\n";
    _paused = true;
    _arduinoPrevTime = 0;
    _overflowCount = 0;
    _sequence_num = 0;
}

void ArduinoFactoryBridge::setInitData(const char *formats, ...)
{
    EXTRACT_DATA_FROM_ARGS();

    _initPacket = data;
}

void ArduinoFactoryBridge::begin() {
    ASYNCIO_ARDUINO_BRIDGE_SERIAL.begin(BAUD_RATE);
}

bool ArduinoFactoryBridge::available() {
    return ASYNCIO_ARDUINO_BRIDGE_SERIAL.available() > 0;
}

int ArduinoFactoryBridge::read()
{
    if (_paused) {
        delay(100);  // minimize activity while paused
    }

    _command = ASYNCIO_ARDUINO_BRIDGE_SERIAL.readStringUntil('\n');
    #ifdef DEBUG
    ASYNCIO_ARDUINO_BRIDGE_SERIAL.println(_command);
    #endif

    if (_command.charAt(0) == '~')
    {
        #ifdef DEBUG
        ASYNCIO_ARDUINO_BRIDGE_SERIAL.println("Non-user command found");
        #endif
        unsigned long new_time;
        switch (_command.charAt(1)) {
            case '>':  // start command
                #ifdef DEBUG
                ASYNCIO_ARDUINO_BRIDGE_SERIAL.println("start command received");
                ASYNCIO_ARDUINO_BRIDGE_SERIAL.print("_paused is ");
                ASYNCIO_ARDUINO_BRIDGE_SERIAL.println(!_paused);
                #endif

                if (_command.length() > 2) {
                    new_time = _command.substring(2).toInt();
                    if (new_time >= DEFAULT_TIME) { // check the integer is a valid time (greater than Jan 1 2013)
                        setTime(new_time); // Sync Arduino clock to the time received on the serial port
                    #ifdef DEBUG
                        ASYNCIO_ARDUINO_BRIDGE_SERIAL.println("Setting to received time");
                    }
                    else {
                        ASYNCIO_ARDUINO_BRIDGE_SERIAL.println("Received time is invalid!");
                    #endif
                    }
                }
                if (unpause()) return 1;
                else return -1;
            case '<':  // stop command
                #ifdef DEBUG
                ASYNCIO_ARDUINO_BRIDGE_SERIAL.println("stop command received");
                ASYNCIO_ARDUINO_BRIDGE_SERIAL.print("_paused is ");
                ASYNCIO_ARDUINO_BRIDGE_SERIAL.println(!_paused);
                #endif
                if (pause()) return 2;
                else return -1;
            case '|':  // get initialization data command
                #ifdef DEBUG
                ASYNCIO_ARDUINO_BRIDGE_SERIAL.println("init command received");
                #endif
                writeInit();
                return 3;
            case '?':  // get board ID command
                #ifdef DEBUG
                ASYNCIO_ARDUINO_BRIDGE_SERIAL.println("whoiam command received");
                #endif
                writeWhoiam();
                return 4;
            #ifndef ARDUINO_RESETS_ON_CONNECT
            case '!':
                writeHello();
                return 5;
            case '+':
                writeReady();
                return 6;
            #endif // ARDUINO_RESETS_ON_CONNECT
        }
    }
    else {
        if (!_paused) return 0;
    }
    return -1;
}

void ArduinoFactoryBridge::changeBaud(int newBaud)
{
    #ifdef DEBUG
    ASYNCIO_ARDUINO_BRIDGE_SERIAL.println("changing baud");
    #endif
    delay(50);
    ASYNCIO_ARDUINO_BRIDGE_SERIAL.end();
    delay(50);
    ASYNCIO_ARDUINO_BRIDGE_SERIAL.begin(newBaud);
}


void ArduinoFactoryBridge::writeWhoiam()
{
    ASYNCIO_ARDUINO_BRIDGE_SERIAL.print("~iam");
    ASYNCIO_ARDUINO_BRIDGE_SERIAL.print(_whoiam);
    ASYNCIO_ARDUINO_BRIDGE_SERIAL.print(PACKET_END);
}

void ArduinoFactoryBridge::writeInit()
{
    ASYNCIO_ARDUINO_BRIDGE_SERIAL.print("~init:");
    ASYNCIO_ARDUINO_BRIDGE_SERIAL.print(_initPacket);
}


void ArduinoFactoryBridge::writeHello()
{
    ASYNCIO_ARDUINO_BRIDGE_SERIAL.print("~hello!");
    ASYNCIO_ARDUINO_BRIDGE_SERIAL.print(PACKET_END);
}

void ArduinoFactoryBridge::writeReady()
{
    ASYNCIO_ARDUINO_BRIDGE_SERIAL.print("~ready!");
    ASYNCIO_ARDUINO_BRIDGE_SERIAL.print(PACKET_END);
}

void ArduinoFactoryBridge::printInt64(int64_t value)
{
    int32_t part1 = value >> 32;
    int32_t part2 = value & 0xffffffff;
    ASYNCIO_ARDUINO_BRIDGE_SERIAL.print(part1);
    ASYNCIO_ARDUINO_BRIDGE_SERIAL.print(":");
    ASYNCIO_ARDUINO_BRIDGE_SERIAL.print(part2);
}

void ArduinoFactoryBridge::printUInt64(uint64_t value)
{
    uint32_t part1 = value >> 32;
    uint32_t part2 = value & 0xffffffff;
    ASYNCIO_ARDUINO_BRIDGE_SERIAL.print(part1);
    ASYNCIO_ARDUINO_BRIDGE_SERIAL.print(":");
    ASYNCIO_ARDUINO_BRIDGE_SERIAL.print(part2);
}

void ArduinoFactoryBridge::writeTime()
{
    uint32_t current_time = micros();
    if (current_time < _arduinoPrevTime) {
        _overflowCount++;
    }
    ASYNCIO_ARDUINO_BRIDGE_SERIAL.print("~ct:");

    ASYNCIO_ARDUINO_BRIDGE_SERIAL.print(_overflowCount);
    ASYNCIO_ARDUINO_BRIDGE_SERIAL.print(':');
    ASYNCIO_ARDUINO_BRIDGE_SERIAL.print(current_time);
    ASYNCIO_ARDUINO_BRIDGE_SERIAL.print(':');
    printUInt64(_sequence_num);
    ASYNCIO_ARDUINO_BRIDGE_SERIAL.print(PACKET_END);

    _arduinoPrevTime = current_time;
    _sequence_num++;
}

void ArduinoFactoryBridge::write(String name, const char *formats, ...)
{
    writeTime();

    EXTRACT_DATA_FROM_ARGS();

    ASYNCIO_ARDUINO_BRIDGE_SERIAL.print(name + "\t" + data);
}

String ArduinoFactoryBridge::getCommand() {
    return _command;
}

bool ArduinoFactoryBridge::isPaused() {
    return _paused;
}

bool ArduinoFactoryBridge::unpause()
{
    if (_paused) {
        _paused = false;
        return true;
    }
    else {
        return false;
    }
}

bool ArduinoFactoryBridge::pause()
{
    if (!_paused) {
        ASYNCIO_ARDUINO_BRIDGE_SERIAL.print("\n~stopping\n");
        _paused = true;
        return true;
    }
    else {
        return false;
    }
}
