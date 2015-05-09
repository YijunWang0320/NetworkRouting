__author__ = 'wangyijun'
import base64

class PacketBuffer(object):
    def __init__(self):
        self.buffer = dict()
        self.size = -1
        self.count = 0
        self.filename = None

    def append(self, message):
        filename = message['filename']
        number = message['number']
        end = message['end']

        if not self.filename:
            self.filename = filename
        else:
            if self.filename != filename:
                return False, True

        if not self.cor_check(message):
            return False, False

        if number not in self.buffer.keys():
            self.buffer[number] = message
            self.count += 1
        if end:
            self.size = number
        if self.size == self.count:
            return True, True
        return False, True

    def make(self):
        wp = open(self.filename, 'wb')
        for i in range(1, self.size):
            if i in self.buffer.keys():
                data = base64.b64decode(self.buffer[i]['data'])
                wp.write(data)
        wp.close()

    def cor_check(self, message):
        data = base64.b64decode(message['data'])
        prior_checksum = message['checksum']
        cur_checksum = self.checksum(data)
        if prior_checksum == cur_checksum:
            return True
        else:
            return False

    def checksum(self, data):
        s = 0
        for i in range(0, len(data), 2):
            if i+1 < len(data):
                w = ord(data[i]) + (ord(data[i+1]) << 8)
            else:
                w = ord(data[i]) + (0 << 8)
            s = self.carry_around_add(s, w)
        return ~s & 0xffff

    def carry_around_add(self, a, b):
        c = a + b
        return (c & 0xffff) + (c >> 16)
