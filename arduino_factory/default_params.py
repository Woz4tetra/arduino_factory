# hello packet
HELLO_PACKET_ASK = "~!"
HELLO_RESPONSE_HEADER = "~hello!"

# ready packet
READY_PACKET_ASK = "~+"
READY_RESPONSE_HEADER = "~ready!"

# whoiam ID info
WHOIAM_PACKET_ASK = "~?"
WHOIAM_RESPONSE_HEADER = "~iam"  # whoiam packets start with "~iam"

# first packet info
FIRST_PACKET_ASK = "~|"
FIRST_RESPONSE_HEADER = "~init:"

STOP_PACKET_ASK = "~<"
STOP_RESPONSE_HEADER = "~stopping"

START_PACKET_ASK = "~>"

TIME_RESPONSE_HEADER = "~ct:"

# misc. device protocol
PROTOCOL_TIMEOUT = 5  # seconds
READY_PROTOCOL_TIMEOUT = 10
PACKET_END = "\n"  # what this microcontroller's packets end with
DEFAULT_RATE = 115200

PORT_UPDATES_PER_SECOND = 1000

INIT_PROTOCOL_PACKETS = [
    HELLO_RESPONSE_HEADER,
    READY_RESPONSE_HEADER,
    WHOIAM_RESPONSE_HEADER,
    FIRST_RESPONSE_HEADER,
    STOP_RESPONSE_HEADER
]

# all runtime protocol packets
RUNTIME_PROTOCOL_PACKETS = [
    TIME_RESPONSE_HEADER
]

DEFAULT_LOG_FORMAT = "[%(name)s @ %(filename)s:%(lineno)d][%(levelname)s] %(asctime)s: %(message)s"