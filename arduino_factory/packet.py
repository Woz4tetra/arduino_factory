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
