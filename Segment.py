__author__ = 'wangyijun'
import json

class Segment(object):
    def __init__(self, data, host_ip, host_port, des_ip, des_port, number, end):
        pack = dict()
        pack['type'] = 'DataTransfer'
        pack['from'] = host_ip + ':' + str(host_port)
        pack['to'] = des_ip + ':' + str(des_port)
        pack['number'] = number
        pack['end'] = end
        self.pack = pack

    def read(self):
        return json.dumps(self.pack)
