import os
import time
import queue
import threading
import multiprocessing

from .packet import Packet
from .default_params import *
from .device_port import DevicePort


class Arduino:
    def __init__(self, whoiam, factory, baud=115200, use_multiprocessing=True):
        if os.name == "nt":
            use_multiprocessing = False

        self._device_port = None
        if use_multiprocessing:
            self._device_start_event = multiprocessing.Event()
            self._device_exit_event = multiprocessing.Event()
            self._device_read_queue = multiprocessing.Queue()
            self._device_write_queue = multiprocessing.Queue()
            self._device_read_lock = multiprocessing.Lock()
            self._device_write_lock = multiprocessing.Lock()
            self._device_process = multiprocessing.Process(target=self._manage_device)
        else:
            self._device_start_event = threading.Event()
            self._device_exit_event = threading.Event()
            self._device_read_queue = queue.Queue()
            self._device_write_queue = queue.Queue()
            self._device_read_lock = threading.Lock()
            self._device_write_lock = threading.Lock()
            self._device_process = threading.Thread(target=self._manage_device)

        self.whoiam = whoiam
        self.start_time = 0.0
        self.first_packet = None
        self._factory = factory
        self.baud = baud
        self.device_port = None

        self._global_sequence_num = 0
        self._arduino_time = 0.0
        self._current_pause_command = None
        # self._prev_arduino_time = 0.0
        self._prev_receive_time = time.time()

        self._factory.arduino_exit_events.append(self._device_exit_event)

    def _manage_device(self):
        try:
            self._poll_device()
        except BaseException:
            self._device_exit_event.set()
            raise

    def _device_active(self):
        return not self._device_exit_event.is_set()

    def read(self, block=True, timeout=1):
        try:
            return self._device_read_queue.get(block, timeout)
        except queue.Empty:
            packet = Packet()
            packet.set_null_params()
            return packet

    def empty(self):
        return self._device_read_queue.empty()

    def write(self, packet):
        with self._device_write_lock:
            self._device_write_queue.put(packet)

    def write_pause(self, pause_time, relative_time=True):
        """
        Send a pause command. This prevents commands from being sent for "pause_time" seconds.
        If relative_time is False, pause_time is the unix timestamp that write will be unfrozen at.
        """
        with self._device_write_lock:
            self._device_write_queue.put(PauseCommand(pause_time, relative_time))

    def clear_write_queue(self):
        with self._device_write_lock:
            if not self._device_write_queue.empty():
                self._factory.logger.debug("Clearing write queue for '%s'" % self.whoiam)
                while not self._device_write_queue.empty():
                    packet = self._device_write_queue.get()
                    self._factory.logger.debug("Cleared packet: '%s'" % packet)

    def start(self):
        if self._device_start_event.is_set():
            self._factory.logger.warning("Start already called for '%s'" % self.whoiam)
            return None
        self._device_port_info = self._factory.get_device(self.whoiam)
        self._device_port_info["baud"] = self.baud
        self._device_port = DevicePort.reinit(self._device_port_info)

        first_packet = self._device_port.first_packet
        self.start_time = self._device_port.start_time
        # self._prev_receive_time = self._device_port.start_time

        self._device_process.start()
        self._device_start_event.set()

        if len(first_packet) > 0:
            name, data = self._parse_data(first_packet, is_first_packet=True)
        else:
            name = "first_packet"
            data = None
        packet_struct = Packet()
        packet_struct.global_sequence_num = -1
        packet_struct.timestamp = 0
        packet_struct.receive_time = time.time()
        packet_struct.name = name
        packet_struct.data = data

        self.first_packet = packet_struct
        return packet_struct

    def stop(self):
        self._device_exit_event.set()

    def _poll_device(self):
        try:
            self._device_port.write_start()

            while self._device_active():
                time.sleep(1 / PORT_UPDATES_PER_SECOND)  # maintain a reasonable loop speed
                if not self._device_port.is_open():
                    self.stop()
                    raise RuntimeError("Serial port isn't open for some reason...")

                self._check_read_queue()
                self._check_write_queue()
        except KeyboardInterrupt:
            pass
        except BaseException:
            raise
        finally:
            # tell the arduino to stop when finished
            self._device_port.stop()

    def _check_read_queue(self):
        # if the arduino has received data
        in_waiting = self._device_port.in_waiting()
        if in_waiting > 0:
            receive_time, packets = self._device_port.read(in_waiting)
            for packet in packets:
                result = self._parse_time_command(packet)
                if result is not None:
                    self._global_sequence_num = result[0]
                    self._arduino_time = result[1]
                    continue

                if self._check_for_protocol_packets(packet):
                    continue

                name, data = self._parse_data(packet)

                packet_struct = Packet()
                packet_struct.global_sequence_num = self._global_sequence_num
                packet_struct.timestamp = self._arduino_time
                packet_struct.receive_time = receive_time
                packet_struct.name = name
                packet_struct.data = data

                # self._prev_receive_time = receive_time

                self._device_read_queue.put(packet_struct)

    def _parse_data(self, packet, is_first_packet=False):
        data = packet.split("\t")[:-1]
        if not is_first_packet:
            name = data.pop(0)
        else:
            name = "first_packet"
        formats = data.pop(0)

        if len(formats) != len(data):
            raise ValueError(
                "Length of formats doesn't equal number of data segments. Name: '%s', formats: '%s', data: '%s'" % (
                    name, formats, data)
            )

        parsed_data = []
        for data_type, datum in zip(formats, data):
            if data_type == 'd':
                parsed_data.append(int(datum))
            elif data_type == 'f':
                parsed_data.append(float(datum))
            else:
                parsed_data.append(datum)

        return name, parsed_data

    def _check_for_protocol_packets(self, packet):
        """Check for misplaced init protocol packet responses (responses to whoareyou, init?, start, stop)"""

        for header in INIT_PROTOCOL_PACKETS:
            if len(packet) >= len(header) and packet[:len(header)] == header:
                # the Arduino can signal to stop if it sends "stopping"
                if header == STOP_RESPONSE_HEADER:
                    self.stop()
                    raise RuntimeError("Port signalled to exit (stop flag was found)", self)
                else:
                    self._factory.logger.warning("Misplaced protocol packet: %s" % repr(packet))
                return True

        return False

    def _parse_time_command(self, packet):
        if len(packet) >= len(TIME_RESPONSE_HEADER) and \
                packet[:len(TIME_RESPONSE_HEADER)] == TIME_RESPONSE_HEADER:
            data = packet[len(TIME_RESPONSE_HEADER):]
            overflow, timer, sequence_num_part1, sequence_num_part2 = data.split(":")
            global_sequence_num = ((int(sequence_num_part1) << 32) | int(sequence_num_part2))
            arduino_time = ((int(overflow) << 32) | int(timer)) / 1E6
            # dt = arduino_time - self._prev_arduino_time
            # self._prev_arduino_time = arduino_time
            #
            # absolute_arduino_time = dt + self._prev_receive_time

            return global_sequence_num, arduino_time
        else:
            return None

    def _check_write_queue(self):
        # prevent the write queue from being accessed while sending commands
        with self._device_write_lock:
            # if the queue isn't currently paused,
            if self._current_pause_command is None:
                # send all commands until it's empty
                if not self._device_write_queue.empty():
                    while not self._device_write_queue.empty():
                        packet = self._device_write_queue.get()

                        # if the command is a pause command, start its timer and stop sending commands
                        if type(packet) == PauseCommand:
                            self._current_pause_command = packet
                            self._current_pause_command.start()
                            break
                        else:
                            self._device_port.write(packet)
            # if the pause command is over, reset current_pause_command
            elif self._current_pause_command.expired():
                self._current_pause_command = None


class PauseCommand:
    """struct holding a pause command telling the command queue to pause for some time"""

    def __init__(self, pause_time, relative_time):
        self.pause_time = pause_time
        self.start_time = 0.0
        self.relative_time = relative_time

    def start(self):
        self.start_time = time.time()

    def expired(self):
        if self.relative_time:
            return time.time() - self.start_time > self.pause_time
        else:
            return time.time() > self.pause_time
