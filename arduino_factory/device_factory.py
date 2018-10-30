import logging
from threading import Thread
from serial.tools import list_ports

from .default_params import *
from .device_port import DevicePort


class DeviceFactory:
    def __init__(self, log_level=logging.INFO, list_devices_fn=None):
        self.ports = {}
        self.arduino_exit_events = []

        if list_devices_fn is None:
            list_devices_fn = DeviceFactory.list_devices_default
        self.list_devices_fn = list_devices_fn

        self.log_level = log_level
        self.make_logger(self.log_level)
        self.is_initialized = False

        self.logger.debug("configuring all connecting devices")
        self.configure_devices()

    def ok(self):
        return all([not event.is_set() for event in self.arduino_exit_events])

    def make_logger(self, level):
        print_handle = logging.StreamHandler()
        print_handle.setLevel(level)
        self.logger = logging.getLogger("Device Factory")
        self.logger.setLevel(level)

        formatter = logging.Formatter(DEFAULT_LOG_FORMAT)
        print_handle.setFormatter(formatter)
        self.logger.addHandler(print_handle)

    @staticmethod
    def list_devices_default():
        """Returns a list of valid possible Arduino USB serial addresses"""
        com_ports = list_ports.comports()

        if len(com_ports) == 0:
            raise RuntimeError("No serial ports found!! "
                               "Try overriding this method with an alternative port finder or "
                               "install the correct drivers")

        addresses = []
        for port_no, description, address in com_ports:
            if 'USB' in address:
                addresses.append(port_no)

        return addresses

    def configure_devices(self):
        """Configure all devices if they haven't been already"""

        # Arduino.ports shared between all Arduino instances. Initialize it if it isn't
        self.logger.info("configuring for the first time")

        addresses = self.list_devices_fn()
        self.logger.info("Found suitable addresses: '%s'" % addresses)

        if len(addresses) == 0:
            raise RuntimeError("Found no valid Arduino addresses!!")

        # start threads that poll all discovered addresses
        self.collect_all_devices(addresses)

        self.logger.info("configuring done")

        self.is_initialized = True

    def collect_all_devices(self, addresses):
        """Initialize all Arduinos on their own threads"""

        tasks = []
        # initialize all discovered ports on its own thread
        for address in addresses:
            config_task = Thread(target=self.configure_devices_task, args=(address,))
            tasks.append((address, config_task))
            config_task.start()

        # wait for all threads to finish
        for address, task in tasks:
            task.join()

    def configure_devices_task(self, address):
        """Threading task to initialize an address"""

        # Attempt to initialize the port. Don't throw an error. It will be handled later
        try:
            device_port = DevicePort.init_configure(address, self.log_level)
        except BaseException as error:
            self.logger.warning(error)
            return

        # if initialized correctly, check for overlap otherwise add it to the ports dictionary
        if device_port.is_arduino:
            port_info = dict(
                whoiam=device_port.whoiam,
                address=device_port.address,
                device=device_port.device,
                start_time=device_port.start_time,
                first_packet=device_port.first_packet,
                log_level=self.log_level
            )
            self.logger.info("address '%s' has ID '%s'" % (device_port.address, device_port.whoiam))

            if device_port.whoiam in self.ports:
                self.logger.info("Address '%s' has the same whoiam ID (%s) as address '%s'" % (
                    device_port.address, device_port.whoiam, self.ports[device_port.whoiam]["address"]))
                self.ports[device_port.whoiam].append(port_info)
            else:

                self.ports[device_port.whoiam] = [port_info]

    def get_device(self, whoiam):
        if not self.is_initialized:
            raise RuntimeError("Factory isn't initialized!! Please call DeviceFactory.configure_devices.")
        if whoiam not in self.ports:
            raise RuntimeError(
                "'whoaim' ID '%s' not found. ID's that were found: %s" % (whoiam, str(list(self.ports.keys())))
            )
        if len(self.ports[whoiam]) == 0:
            raise RuntimeError("No ports found! Invalid situation. Should have been caught by list addresses")

        return self.ports[whoiam].pop(0)

    def stop_all(self):
        for device_ports in self.ports.values():
            for device_port in device_ports:
                self.logger.info("Stopping '%s' with address '%s'" % (device_port.whoiam, device_port.address))
                device_port.stop()

        for event in self.arduino_exit_events:
            event.set()
