import time
from arduino_factory import Arduino, DeviceFactory

factory = DeviceFactory()
test = Arduino("test", factory)

first_packet = test.start()
print("first packet:", first_packet)
try:
    while factory.ok():
        packet = test.read()
        if packet.name == "numbers":
            if packet.data[0] >= 12:
                test.write("d")
                test.write("f")
                test.write("s1")
                test.write("s2")
        current_time = time.time()
        print(
            "local: %0.4f, arduino: %0.4f, diff: %0.4f, data: %s" % (
                current_time - test.start_time,
                packet.timestamp - test.start_time,
                current_time - packet.timestamp,
                packet.data)
        )
except KeyboardInterrupt:
    pass
except BaseException:
    raise
finally:
    factory.stop_all()
