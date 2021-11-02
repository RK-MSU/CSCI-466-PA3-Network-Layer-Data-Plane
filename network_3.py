# network_3.py

import queue
import threading
from rprint import print


# wrapper class for a queue of packets
class Interface:
    # @param max_queue_size - the maximum size of the queue storing packets
    #  @param mtu - the maximum transmission unit on this interface
    def __init__(self, max_queue_size=0):
        self.queue = queue.Queue(max_queue_size)
        self.mtu = 1
    
    # get packet from the queue interface
    def get(self):
        try:
            return self.queue.get(False)
        except queue.Empty:
            return None
    
    # put the packet into the interface queue
    # @param pkt - Packet to be inserted into the queue
    # @param block - if True, block until room in queue, if False may throw queue.Full exception
    def put(self, pkt, block=False):
        self.queue.put(pkt, block)


# Implements a network layer packet (different from the RDT packet
# from programming assignment 2).
# NOTE: This class will need to be extended to for the packet to include
# the fields necessary for the completion of this assignment.
class NetworkPacket:
    # packet encoding lengths
    dst_addr_S_length = 5
    id_S_length = 2
    flag_S_length = 1
    offset_S_length = 2
    header_S_length = dst_addr_S_length + id_S_length + flag_S_length + offset_S_length
    id = 0
    flag = 0
    offset = 0
    
    #@param dst_addr: address of the destination host
    # @param data_S: packet payload
    def __init__(self, dst_addr, data_S, id=1, flag=0, offset=0):
        self.dst_addr = dst_addr
        self.data_S = data_S
        self.id = id
        self.flag = flag
        self.offset = offset
    
    # called when printing the object
    def __str__(self):
        return self.to_byte_S()
    
    def __len__(self):
        return len(self.to_byte_S)
    
    # convert packet to a byte string for transmission over links
    def to_byte_S(self):
        byte_S = ''
        byte_S += str(self.id).zfill(self.id_S_length)
        byte_S += str(self.flag).zfill(self.flag_S_length)
        byte_S += str(self.offset).zfill(self.offset_S_length)
        byte_S += str(self.dst_addr).zfill(self.dst_addr_S_length)
        byte_S += self.data_S
        return byte_S
    
    # extract a packet object from a byte string
    # @param byte_S: byte string representation of the packet
    @classmethod
    def from_byte_S(self, byte_S):
        m = NetworkPacket.id_S_length
        id = int(byte_S[:m])
        flag = int(byte_S[m : m + NetworkPacket.flag_S_length])
        m += NetworkPacket.flag_S_length
        offset = int(byte_S[m : m + NetworkPacket.offset_S_length])
        m += NetworkPacket.offset_S_length
        dst_addr = int(byte_S[m : m + NetworkPacket.dst_addr_S_length])
        m += NetworkPacket.dst_addr_S_length
        data_S = byte_S[m:]
        return self(dst_addr, data_S, id, flag, offset)


# Implements a network host for receiving and transmitting data
class Host:
    
    #@param addr: address of this node represented as an integer
    def __init__(self, addr):
        self.addr = addr
        self.in_intf_L = [Interface()]
        self.out_intf_L = [Interface()]
        self.stop = False  # for thread termination
        self.fragments = list()
    
    # called when printing the object
    def __str__(self):
        return 'Host_%s' % (self.addr)
    
    # create a packet and enqueue for transmission
    # @param dst_addr: destination address for the packet
    # @param data_S: data being transmitted to the network layer
    def udt_send(self, dst_addr, data_S, id, mtu=None, offset=0):
        if mtu is None: mtu = self.out_intf_L[0].mtu
        msg_length = offset + mtu - NetworkPacket.header_S_length
        if NetworkPacket.header_S_length + len(data_S) > mtu:
            flag = int(NetworkPacket.header_S_length + len(data_S) > mtu * 2)
            p = NetworkPacket(dst_addr, data_S[offset:msg_length], id, flag, offset)
            print('%s: sending packet "%s" on the out interface with mtu=%d' % (self, p, mtu))
            self.out_intf_L[0].put(p.to_byte_S())
            self.udt_send(dst_addr, data_S[offset:], id, mtu, msg_length - offset)
    
    # receive packet from the network layer
    def udt_receive(self):
        pkt_S = self.in_intf_L[0].get()
        if pkt_S is not None:
            p = NetworkPacket.from_byte_S(pkt_S)
            self.fragments.append(p)
            message_data = ''
            if p.flag == 0:
                for frag in self.fragments:
                    if frag.id == p.id:  message_data += frag.data_S
                print('%s: received packet "%s" on the in interface' % (self, message_data))
    
    # thread target for the host to keep receiving data
    def run(self):
        print(threading.currentThread().getName() + ': Starting')
        while True:
            # receive data arriving to the in interface
            self.udt_receive()
            # terminate
            if (self.stop):
                print(threading.currentThread().getName() + ': Ending')
                return


# Implements a multi-interface router described in class
class Router:
    
    #@param name: friendly router name for debugging
    # @param intf_count: the number of input and output interfaces
    # @param max_queue_size: max queue length (passed to Interface)
    def __init__(self, name, intf_count, max_queue_size):
        self.stop = False  # for thread termination
        self.name = name
        # create a list of interfaces
        self.in_intf_L = [Interface(max_queue_size) for _ in range(intf_count)]
        self.out_intf_L = [Interface(max_queue_size) for _ in range(intf_count)]
    
    # called when printing the object
    def __str__(self):
        return 'Router_%s' % (self.name)
    
    # look through the content of incoming interfaces and forward to
    # appropriate outgoing interfaces
    def forward(self):
        for i in range(len(self.in_intf_L)):
            pkt_S = None
            try:
                # get packet from interface i
                pkt_S = self.in_intf_L[i].get()
                if pkt_S is not None:
                    p = NetworkPacket.from_byte_S(pkt_S)  # parse a packet out
                    self.handle_frag(p, i, i, self.out_intf_L[i].mtu)
            except queue.Full:
                print('%s: packet "%s" lost on interface %d' % (self, p, i))
                pass
    
    def handle_frag(self, packet, src, dst, mtu, offset=0):
        if NetworkPacket.header_S_length + len(packet.data_S) > mtu:
            p = NetworkPacket(packet.dst_addr, packet.data_S[offset:offset + mtu - NetworkPacket.header_S_length], packet.id, 1, offset=offset)
            print('%s: forwarding packet "%s" from interface %d to %d with mtu %d' % (self, p, src, dst, mtu))
            self.out_intf_L[dst].put(p.to_byte_S())
        else:
            print('%s: forwarding packet "%s" from interface %d to %d with mtu %d' % (self, packet, src, dst, mtu))
            self.out_intf_L[dst].put(packet.to_byte_S())
            return
        offset = offset + mtu - NetworkPacket.header_S_length - offset
        packet.data_S = packet.data_S[offset:]
        self.handle_frag(packet, src, dst, mtu, offset)
    
    # thread target for the host to keep forwarding data
    def run(self):
        print(threading.currentThread().getName() + ': Starting')
        while True:
            self.forward()
            if self.stop:
                print(threading.currentThread().getName() + ': Ending')
                return

# EOF