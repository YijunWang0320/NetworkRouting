__author__ = 'wangyijun'
from WatchDog import WatchDog
import cPickle as pickle


class PacketTracker(object):
    def __init__(self, timeout):
        self.tracker = dict()
        self.fileCount = dict()
        self.timeout = timeout

    def start(self, filename):
        self.fileCount[filename] = 0

    def add(self, segment, hop_ip, hop_port, server_sock):
        data = pickle.loads(segment)
        filename = data['filename']
        number = data['number']
        self.fileCount[filename] += 1
        self.tracker[(filename, number)] = WatchDog(self.timeout, [data, hop_ip, hop_port, server_sock], self.resend)
        self.tracker[(filename, number)].start()

    def resend(self, data, hop_ip, hop_port, server_sock):
        filename = data['filename']
        number = data['number']
        server_sock.sendto(pickle.dumps(data), (hop_ip, hop_port))
        self.tracker[(filename, number)].reset()
        self.tracker[(filename, number)].start()

    def acknowledge(self, filename, number):
        if self.tracker[(filename, number)]:
            self.tracker[(filename, number)].stop()
            self.tracker[(filename, number)] = None
            self.fileCount[filename] -= 1
            if self.fileCount[filename] == 0:
                return True
        return False