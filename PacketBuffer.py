__author__ = 'wangyijun'

class PacketBuffer(object):
    def __init__(self):
        self.buffer = dict()
        self.size = 0
        self.filename = None

    def append(self, message):
        filename = message['filename']
        number = message['number']
        end = message['end']
        if not self.filename:
            self.filename = filename
        else:
            if self.filename != filename:
                return False

        if number > self.size:
            self.size = number
        if end:
            return True
        self.buffer[number] = message
        return False

    def make(self):
        wp = open(self.filename, 'wb')
        for i in range(1, self.size):
            if i in self.buffer.keys():
                data = self.buffer[i]['data']
                wp.write(data)
        wp.close()
