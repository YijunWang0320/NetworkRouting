__author__ = 'wangyijun'
import sys
import socket
from RoutingTable import RoutingTable
from collections import defaultdict
import cPickle as pickle
import datetime
import select
from WatchDog import WatchDog
from Segment import Segment
from PacketBuffer import PacketBuffer
from PacketTracker import PacketTracker

# The global variables
host_ip = ''
host_port = 0
timeout = 0            # timeout set
routing_table = None   # the routing table
sock_list = []         # managing stdin and udp sock
server_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
watchDog = None        # the one sending out the routing message
timer_dict = dict()        # the one keep track of the heart beat message
MSS = 300              # Maximum size of a datagram
server_buffer = defaultdict(PacketBuffer)   # have a buffer for every (ip, port) pair that send packet to host
proxy_server_list = dict()                  # keep track of all the proxy servers
packetTracker = PacketTracker(5)             # The packetTrack to keep track of all the ACKs


def add_proxy(proxy_ip, proxy_port, neighbor_ip, neighbor_port):
    proxy_server_list[(neighbor_ip, neighbor_port)] = (proxy_ip, proxy_port)


def remove_proxy(neighbor_ip, neighbor_port):
    proxy_server_list[(neighbor_ip, neighbor_port)] = None


def send_update():
    global routing_table
    global watchDog
    for key in routing_table.get_neighbors():
        send_routing_message(key[0], key[1])
    watchDog.reset()
    watchDog.start()
    return


def time_up(key):
    global timer_dict
    global routing_table
    ip = key[0]
    port = key[1]
    watchDog = timer_dict[key]
    routing_table.neighbor_linkdown(ip, port)
    watchDog.reset()
    return


def send_routing_message(ip, port):
    global routing_table
    global host_ip
    global host_port
    global server_sock
    send_dict = dict()
    send_dict['type'] = 'RoutingUpdate'
    send_dict['from'] = host_ip + ':' + str(host_port)
    temp = list()
    routing_table.lock.acquire()
    for item in routing_table.get_keySet():
        far_ip = item[0]
        far_port = item[1]
        temp.append(far_ip + ':' + str(far_port) + ':' + str(routing_table.get_edge_weight(host_ip, host_port, item[0], item[1])) +
                    ':' + routing_table.get_edge_through(host_ip, host_port, item[0], item[1])[0] + ':' + str(routing_table.get_edge_through(host_ip, host_port, item[0], item[1])[1]))
    routing_table.lock.release()
    send_dict['message'] = tuple(temp)
    server_sock.sendto(pickle.dumps(send_dict), (ip, port))


def transfer_file(filename, des_ip, des_port):
    global host_ip
    global host_port
    global routing_table
    global MSS
    global proxy_server_list
    global packetTracker
    if (des_ip, des_port) not in routing_table.get_keySet():
        print 'Sorry, cannot route to the destination'
        return
    fp = open(filename, 'r+b')
    hop_ip = routing_table.get_edge_through(host_ip, host_port, des_ip, des_port)[0]
    hop_port = routing_table.get_edge_through(host_ip, host_port, des_ip, des_port)[1]
    print 'Next hop = ' + hop_ip + ':' + str(hop_port)
    if (hop_ip, hop_port) in proxy_server_list.keys() and proxy_server_list[(hop_ip, hop_port)]:
        hop_ip = proxy_server_list[(hop_ip, hop_port)][0]
        hop_port = proxy_server_list[(hop_ip, hop_port)][1]
    packetTracker.start(filename)
    try:
        data = 'y'
        count = 1
        while data != '':
            data = fp.read(MSS)
            segment = Segment(filename, data, host_ip, host_port, des_ip, des_port, count, False)
            packetTracker.add(segment.read(), hop_ip, hop_port, server_sock)
            server_sock.sendto(segment.read(), (hop_ip, hop_port))
            count += 1
        segment = Segment(filename, data, host_ip, host_port, des_ip, des_port, count, True)
        packetTracker.add(segment.read(), hop_ip, hop_port, server_sock)
        server_sock.sendto(segment.read(), (hop_ip, hop_port))
    finally:
        fp.close()
    return


def init_host(config_file):
    global host_ip
    global host_port
    global timeout
    global routing_table
    global watchDog
    global timer_dict
    global proxy_server_list
    fp = open(config_file)
    count = 1
    for line in fp:
        if count == 1:
            para = line.strip().split()
            host_ip = socket.gethostbyname(socket.gethostname())
            host_port = int(para[0])
            timeout = float(para[1])
            routing_table = RoutingTable(host_ip, host_port)
        else:
            routing_table.lock.acquire()
            para = line.strip().split()
            # splitting the ip and port
            t_para = para[0].split(':')
            # initiate the weight
            routing_table.set_neighbor(t_para[0], int(t_para[1]), float(para[1]))
            routing_table.set_edge_weight(host_ip, host_port, t_para[0], int(t_para[1]), float(para[1]))
            routing_table.set_edge_through(host_ip, host_port, t_para[0], int(t_para[1]), t_para[0], int(t_para[1]))
            routing_table.lock.release()
        count += 1
    fp.close()
    routing_table.lock.acquire()
    routing_table.set_edge_weight(host_ip, host_port, host_ip, host_port, 0.0)
    routing_table.set_edge_through(host_ip, host_port, host_ip, host_port, host_ip, host_port)
    routing_table.lock.release()
    '''
        This is just added for part three
        having a proxy list
    '''
    for each in routing_table.get_all_neighbors():
        proxy_server_list[each] = None

    watchDog = WatchDog(timeout, [], send_update)
    watchDog.start()
    for key in routing_table.neighbor.keys():
        timer = WatchDog(3*timeout, [key], time_up)
        timer.start()
        timer_dict[key] = timer


def dealWithCommand(command):
    global host_ip
    global host_port
    global timeout
    global routing_table
    var = command.strip().split()
    if var[0] == 'SHOWRT':
        if len(var) != 1:
            raise
        current_time = datetime.datetime.now()
        print '<' + str(current_time) + '>' + ' ' + 'Distance vector list is:'
        routing_table.doPrint()
    elif var[0] == 'LINKDOWN':
        if len(var) != 3:
            raise
        t_ip = var[1]
        t_port = int(var[2])
        routing_table.neighbor_linkdown(t_ip, t_port)
    elif var[0] == 'LINKUP':
        if len(var) != 3:
            raise
        t_ip = var[1]
        t_port = int(var[2])
        routing_table.neighbor_linkup(t_ip, t_port)
    elif var[0] == 'print':
        if len(var) != 5:
            raise
        from_ip = var[1]
        from_port = int(var[2])
        d_ip = var[3]
        d_port = int(var[4])
        print routing_table.get_edge_weight(from_ip, from_port, d_ip, d_port)
    elif var[0] == 'CHANGECOST':
        if len(var) != 4:
            raise
        if routing_table.neighbor_check(var[1], var[2]):
            routing_table.change_weight(var[1], var[2], var[3])
        else:
            pass
    elif var[0] == 'CLOSE':
        if len(var) != 1:
            raise
        return False

    elif var[0] == 'TRANSFER':
        if len(var) != 4:
            raise
        filename = var[1]
        des_ip = var[2]
        des_port = int(var[3])
        transfer_file(filename, des_ip, des_port)
    elif var[0] == 'ADDPROXY':
        if len(var) != 5:
            raise
        proxy_ip = var[1]
        proxy_port = int(var[2])
        neighbor_ip = var[3]
        neighbor_port = int(var[4])
        add_proxy(proxy_ip, proxy_port, neighbor_ip, neighbor_port)
    else:
        pass
    return True





'''
    What is like in the message?
    Updates:
        'from': ip:port
        'meesage': (tuples)  every tuple:(ip:port:weight)
'''
def dealWithSock(message):
    global host_ip
    global host_port
    global timeout
    global routing_table
    global timer_dict
    global server_buffer
    global server_sock
    global packetTracker
    if 'type' not in message.keys():
        raise
    else:
        if message['type'] == 'RoutingUpdate':
            come_ip = message['from'].split(':')[0]
            come_port = int(message['from'].split(':')[1])

            if not routing_table.neighbor_check(come_ip, come_port):
                routing_table.neighbor_linkup(come_ip, come_port)
            watchDog = timer_dict[(come_ip, come_port)]
            watchDog.reset()
            watchDog.start()

            routing_table.lock.acquire()
            for i in range(0, len(message['message'])):
                cur_line = message['message'][i]
                cur_tuples = cur_line.split(':')
                far_ip = cur_tuples[0]
                far_port = float(cur_tuples[1])
                far_weight = float(cur_tuples[2])
                far_through_ip = cur_tuples[3]
                far_through_port = int(cur_tuples[4])

                if far_ip == host_ip and far_port == host_port:
                        continue

                if far_through_ip == host_ip and far_through_port == host_port:
                    far_weight = sys.maxint

                routing_table.set_edge_weight(come_ip, come_port, far_ip, far_port, far_weight)
                routing_table.set_edge_through(come_ip, come_port, far_ip, far_port, far_through_ip, far_through_port)

                routing_table.set_edge_weight(host_ip, host_port, far_ip, far_port, sys.maxint)

                for (from_ip, from_port) in routing_table.get_all_neighbors():

                    if routing_table.has_edge(from_ip, from_port, far_ip, far_port):
                        far_weight = routing_table.get_edge_weight(from_ip, from_port, far_ip, far_port)
                    else:
                        continue
                    # recalculate the weight of a path
                    if not routing_table.has_node(far_ip, far_port):
                        temp_weight = far_weight + routing_table.get_neighbor_weight(from_ip, from_port)
                        routing_table.set_edge_weight(host_ip, host_port, far_ip, far_port,
                                                      min(temp_weight, sys.maxint))
                        routing_table.set_edge_through(host_ip, host_port, far_ip, far_port, from_ip, from_port)
                    else:
                        temp_weight = far_weight + routing_table.get_neighbor_weight(from_ip, from_port)
                        if temp_weight < routing_table.get_edge_weight(host_ip, host_port, far_ip, far_port):
                            routing_table.set_edge_weight(host_ip, host_port, far_ip, far_port, min(sys.maxint, temp_weight))
                            routing_table.set_edge_through(host_ip, host_port, far_ip, far_port, from_ip, from_port)
                        else:
                            pass
            routing_table.lock.release()
        elif message['type'] == 'DataTransfer':
            des_ip = message['to'].split(':')[0]
            des_port = int(message['to'].split(':')[1])
            from_ip = message['from'].split(':')[0]
            from_port = int(message['from'].split(':')[1])
            if des_ip == host_ip and des_port == host_port:
                if (des_ip, des_port) not in server_buffer.keys():
                    server_buffer[(des_ip, des_port)] = PacketBuffer()
                ret = server_buffer[(des_ip, des_port)].append(message)
                server_sock.sendto(pickle.dumps({'type': 'ACK', 'ip': des_ip, 'port': des_port, 'filename': message['filename'], 'number': message['number']}), (from_ip, from_port))
                if ret:
                    server_buffer[(des_ip, des_port)].make()
                    server_buffer[(des_ip, des_port)] = PacketBuffer()
                    print 'Packet received'
                    print 'Source = ' + message['from']
                    print 'Destination = ' + message['to']
                    print 'File received successfully'
                    sys.stdout.write('%>')
                    sys.stdout.flush()
            else:
                if (des_ip, des_port) not in routing_table.get_keySet():
                    raise
                else:
                    # we should forward this segment to the destination
                    hop_ip = routing_table.get_edge_through(host_ip, host_port, des_ip, des_port)[0]
                    hop_port = routing_table.get_edge_through(host_ip, host_port, des_ip, des_port)[1]
                    print 'Packet received'
                    print 'Source = ' + message['from']
                    print 'Destination' + message['to']
                    print 'Next hop = ' + host_ip + ':' + str(hop_port)
                    sys.stdout.write('%>')
                    sys.stdout.flush()
                    server_sock.sendto(pickle.dumps(message), (hop_ip, hop_port))
        elif message['type'] == 'ACK':
            flag = packetTracker.acknowledge(message['filename'], message['number'])
            if flag:
                print 'File sent successfully'
                sys.stdout.write('%>')
                sys.stdout.flush()
            pass
        else:
            pass

    return


def main():
    global host_ip
    global host_port
    global timeout
    global routing_table
    global server_sock
    global sock_list
    if len(sys.argv) != 2:
        print 'We need one argument to specify the filename'
        sys.exit()
    config_file = sys.argv[1]
    try:
        init_host(config_file)
    except KeyboardInterrupt:
        raise
    except:
        print 'The init file need to follow the format'
        sys.exit()

    server_sock.bind((host_ip, host_port))
    sock_list.append(server_sock)
    sock_list.append(sys.stdin)
    sys.stdout.write('%>')
    sys.stdout.flush()
    while True:
        read_sockets, write_sockets, error_sockets = select.select(sock_list, [], [])
        for sock in read_sockets:
            if sock is sys.stdin:
                line = sock.readline()
                try:
                    ret = dealWithCommand(line)
                    if not ret:
                        return
                except KeyboardInterrupt:
                    raise
                except:
                    print 'command must be wrong or argument number is wrong'
                sys.stdout.write('%>')
                sys.stdout.flush()
            else:
                data, addr = sock.recvfrom(8196, socket.MSG_DONTWAIT)
                line = pickle.loads(data)
                #try:
                dealWithSock(line)
                #except KeyboardInterrupt:
                    #raise
                #except:
                    #print 'exception happened in messaging process'


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
    print 'Successfully exit the program'
    watchDog.stop()
    for key in timer_dict.keys():
        timer = timer_dict[key]
        timer.stop()
    server_sock.close()
    sys.exit()