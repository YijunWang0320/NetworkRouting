__author__ = 'wangyijun'
from collections import defaultdict
import sys
import threading

class RoutingTable(object):
    # We might need a lock if we want multiple thread access
    def __init__(self, host_ip, host_port):
        self.table = defaultdict(lambda: defaultdict(dict))
        self.neighbor = defaultdict(dict)
        self.host_ip = host_ip
        self.host_port = host_port
        self.lock = threading.Lock()


    def set_edge_weight(self, from_ip, from_port, to_ip, to_port, weight):
        self.table[(from_ip, from_port)][(to_ip, to_port)]['weight'] = weight

    def set_edge_through(self, from_ip, from_port, to_ip, to_port, t_ip, t_port):
        self.table[(from_ip, from_port)][(to_ip, to_port)]['through'] = (t_ip, t_port)

    def set_neighbor(self, ip, port, weight):
        self.neighbor[(ip, port)]['weight'] = weight
        self.neighbor[(ip, port)]['origin'] = weight

    def get_neighbor_weight(self, ip, port):
        temp = self.neighbor[(ip, port)]['weight']
        return temp

    def get_edge_weight(self, from_ip, from_port, to_ip, to_port):
        temp = self.table[(from_ip, from_port)][(to_ip, to_port)]['weight']
        return temp

    def get_edge_through(self, from_ip, from_port, to_ip, to_port):
        temp = self.table[(from_ip, from_port)][(to_ip, to_port)]['through']
        return temp

    '''
        This part is the command part

    '''

    def neighbor_linkdown(self, ip, port):
        if (ip, port) not in self.get_all_neighbors():
            return
        self.lock.acquire()
        self.neighbor[(ip, port)]['weight'] = sys.maxint
        for point in self.table[(self.host_ip, self.host_port)].keys():
            if point[0] == self.host_ip and point[1] == self.host_port:
                continue
            else:
                if self.table[(self.host_ip, self.host_port)][(point[0], point[1])]['through'] == (ip, port):
                    self.table[(self.host_ip, self.host_port)][(point[0], point[1])]['weight'] = sys.maxint
                for key in self.neighbor.keys():
                    if point in self.table[key].keys():
                        if self.neighbor[(key[0], key[1])]['weight'] + self.table[(key[0], key[1])][(point[0], point[1])]['weight'] < self.table[(self.host_ip, self.host_port)][(point[0], point[1])]['weight']:
                            self.table[(self.host_ip, self.host_port)][(point[0], point[1])]['weight'] = self.neighbor[(key[0], key[1])]['weight'] + self.table[(key[0], key[1])][(point[0], point[1])]['weight']
                            self.table[(self.host_ip, self.host_port)][(point[0], point[1])]['through'] = (key[0], key[1])
        self.lock.release()


    def neighbor_linkup(self, ip, port):
        if (ip, port) not in self.get_all_neighbors():
            return
        self.lock.acquire()
        self.neighbor[(ip, port)]['weight'] = self.neighbor[(ip, port)]['origin']
        for point in self.table[(self.host_ip, self.host_port)].keys():
            if point[0] == self.host_ip and point[1] == self.host_port:
                continue
            else:
                self.table[(self.host_ip, self.host_port)][(point[0], point[1])]['weight'] = sys.maxint
                for key in self.neighbor.keys():
                    if point in self.table[key].keys():
                        if self.neighbor[(key[0], key[1])]['weight'] + self.table[(key[0], key[1])][(point[0], point[1])]['weight'] < self.table[(self.host_ip, self.host_port)][(point[0], point[1])]['weight']:
                            self.table[(self.host_ip, self.host_port)][(point[0], point[1])]['weight'] = self.neighbor[(key[0], key[1])]['weight'] + self.table[(key[0], key[1])][(point[0], point[1])]['weight']
                            self.table[(self.host_ip, self.host_port)][(point[0], point[1])]['through'] = (key[0], key[1])
        self.lock.release()

    def change_cost(self, ip, port, cost):
        if (ip, port) not in self.get_all_neighbors():
            return
        self.lock.acquire()
        self.neighbor[(ip, port)]['weight'] = cost
        self.neighbor[(ip, port)]['origin'] = cost
        for point in self.table[(self.host_ip, self.host_port)].keys():
            if point[0] == self.host_ip and point[1] == self.host_port:
                continue
            else:
                self.table[(self.host_ip, self.host_port)][(point[0], point[1])]['weight'] = sys.maxint
                for key in self.neighbor.keys():
                    if point in self.table[key].keys():
                        if self.neighbor[(key[0], key[1])]['weight'] + self.table[(key[0], key[1])][(point[0], point[1])]['weight'] < self.table[(self.host_ip, self.host_port)][(point[0], point[1])]['weight']:
                            self.table[(self.host_ip, self.host_port)][(point[0], point[1])]['weight'] = self.neighbor[(key[0], key[1])]['weight'] + self.table[(key[0], key[1])][(point[0], point[1])]['weight']
                            self.table[(self.host_ip, self.host_port)][(point[0], point[1])]['through'] = (key[0], key[1])
        self.lock.release()

    '''
        The end of the command part
    '''

    def neighbor_check(self, ip, port):
        return self.neighbor[(ip, port)]['weight'] != sys.maxint

    def has_node(self, ip, port):
        if (ip, port) in self.table[(self.host_ip, self.host_port)].keys():
            return True
        else:
            return False

    def has_edge(self, from_ip, from_port, to_ip, to_port):
        if (from_ip, from_port) in self.table.keys() and (to_ip, to_port) in self.table[(from_ip, from_port)].keys():
            return True
        else:
            return False

    def get_keySet(self):
        return self.table[(self.host_ip, self.host_port)].keys()

    def get_neighbors(self):
        relist = []
        for key in self.neighbor.keys():
            if self.neighbor[key]['weight'] != sys.maxint:
                relist.append(key)
        return relist

    def get_all_neighbors(self):
        return self.neighbor.keys()

    def doPrint(self):
        self.lock.acquire()
        for key in self.table[(self.host_ip, self.host_port)].keys():
            print 'Destination = ' + key[0] + ':' + str(key[1]) + ',' + 'Cost = ' + str(self.table[(self.host_ip, self.host_port)][key]['weight']) + ','\
                  + 'Link = (' + self.table[(self.host_ip, self.host_port)][key]['through'][0] + ':' + str(self.table[(self.host_ip, self.host_port)][key]['through'][1]) + ')'
        self.lock.release()

