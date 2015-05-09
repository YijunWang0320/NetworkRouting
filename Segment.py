__author__ = 'wangyijun'
import base64
import cPickle as pickle


class Segment(object):
    def __init__(self, filename, data, host_ip, host_port, des_ip, des_port, number, end):
        pack = dict()
        pack['type'] = 'DataTransfer'
        pack['filename'] = filename
        pack['data'] = base64.b64encode(data)
        pack['from'] = host_ip + ':' + str(host_port)
        pack['to'] = des_ip + ':' + str(des_port)
        pack['number'] = number
        pack['end'] = end
        pack['checksum'] = self.checksum(str(data))
        self.pack = pack

    def read(self):
        return pickle.dumps(self.pack)

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

