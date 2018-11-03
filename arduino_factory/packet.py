import re

class Packet:
    def __init__(self):
        self.name = ""
        self.data = []
        self.receive_time = 0.0
        self.timestamp = 0.0
        self.global_sequence_num = 0
        self.sequence_num = 0

    def set_null_params(self):
        self.name = None
        self.data = None
        self.receive_time = 0.0
        self.timestamp = 0.0
        self.global_sequence_num = -1
        self.sequence_num = -1

    def __str__(self):
        string = "%s(" % self.__class__.__name__
        for key, value in self.__dict__.items():
            string += "%s=%s, " % (key, value)
        return string[:-2] + ")"

def parse(string):
    packet = Packet()

    global_regex = r"Packet(\(.*\))"

    match = re.search(global_regex, string)
    if match is None or len(match.groups()) == 0:
        return None

    string = match.group(1)

    float_regex = r"[-+]?(?:(?:\d*\.\d+)|(?:\d+\.?))(?:[Ee][+-]?\d+)?"
    int_regex = r"[-+]?[0-9]+"

    timestamp_regex = re.compile("[, (]timestamp=(%s)[, )]" % float_regex)
    global_sequence_num_regex = re.compile("[, (]global_sequence_num=(%s)[,)]" % int_regex)
    receive_time_regex = re.compile("[, (]receive_time=(%s)[, )]" % float_regex)
    sequence_num_regex = re.compile("[, (]sequence_num=(%s)[, )]" % float_regex)
    name_regex = r"[, (]name=(.*?)[, )]"
    data_regex = r"[, (]data=\[(.*?)\][, )]"

    all_regexes = {
        "timestamp": (timestamp_regex, float),
        "global_sequence_num": (global_sequence_num_regex, int),
        "receive_time": (receive_time_regex, float),
        "sequence_num": (sequence_num_regex, int),
        "name": (name_regex, str),
        "data": (data_regex, str)
    }

    for name, info in all_regexes.items():
        regex, data_type = info
        match = re.search(regex, string)
        if match is None:
            raise ValueError("Couldn't find required property '%s' in string '%s'" % (name, string))
        packet.__dict__[name] = data_type(match.group(1))

    parsed_data = []
    for segment in packet.data.split(", "):
        parsed_datum = None
        if re.search(float_regex, segment):
            parsed_datum = float(segment)
        elif re.search(int_regex, segment):
            parsed_datum = int(segment)
        else:
            parsed_datum = str(segment)
        parsed_data.append(parsed_datum)
    packet.data = parsed_data

    return packet
