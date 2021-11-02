# network_2.py

import queue
import threading
import math
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
    id_len = 2
    flag_len = 1
    offset_len = 4
    header_len = dst_addr_S_length + id_len + flag_len + offset_len

    pkt_id = 0
    offset = 0
    frag = 0
    
    #@param dst_addr: address of the destination host
    # @param data_S: packet payload
    def __init__(self, dst_addr, data_S, id=0, offset=0, frag=0):
        self.dst_addr = dst_addr
        self.data_S = data_S
        self.pkt_id = id
        self.offset = offset
        # self.frag = frag
        if frag:
            self.frag = 1 # true
        else:
            self.frag = 0 # false
    
    # called when printing the object
    def __str__(self):
        return self.to_byte_S()
    
    # convert packet to a byte string for transmission over links
    def to_byte_S(self):
        byte_S = str(self.pkt_id).zfill(self.id_len)
        byte_S += str(self.offset).zfill(self.offset_len)
        byte_S += str(self.frag).zfill(self.flag_len)
        byte_S += str(self.dst_addr).zfill(self.dst_addr_S_length)
        byte_S += self.data_S
        return byte_S

    def __str__(self):
        return self.to_byte_S()

    def __len__(self):
        return(len(self.to_byte_S()))
    
    # extract a packet object from a byte string
    # @param byte_S: byte string representation of the packet
    @classmethod
    def from_byte_S(self, byte_S):
        # ID
        id = int(byte_S[0: NetworkPacket.id_len])

        length = NetworkPacket.id_len + NetworkPacket.offset_len
        offset = int(byte_S[NetworkPacket.id_len: length])

        length = NetworkPacket.id_len + NetworkPacket.offset_len + NetworkPacket.flag_len
        frag = int(byte_S[(NetworkPacket.id_len + NetworkPacket.offset_len): length])

        dst_addr = int(byte_S[(NetworkPacket.header_len-NetworkPacket.dst_addr_S_length): NetworkPacket.header_len])
        data_S = byte_S[NetworkPacket.header_len:]

        return self(dst_addr, data_S, id, offset, frag)


# Implements a network host for receiving and transmitting data
class Host:
    pktID = 0
    pkt = None
    #@param addr: address of this node represented as an integer
    def __init__(self, addr):
        self.addr = addr
        self.in_intf_L = [Interface()]
        self.out_intf_L = [Interface()]
        self.stop = False  # for thread termination
    
    # called when printing the object
    def __str__(self):
        return 'Host_%s' % (self.addr)
    
    # create a packet and enqueue for transmission
    # @param dst_addr: destination address for the packet
    # @param data_S: data being transmitted to the network layer
    def udt_send(self, dst_addr, data_S):
        mtu = self.out_intf_L[0].mtu
        if len(data_S) > self.out_intf_L[0].mtu:
            offset = 0
            frag = 1
            div = mtu - (NetworkPacket.header_len)
            numPkt = math.ceil(len(data_S)/div)
            print('%s: segmenting packet "%s" into %s packets for the out interface with mtu=%d' % (self, data_S, numPkt, mtu))
            for i in range(0, numPkt):
                if(i == (numPkt-1)):
                    frag = 0
                p = NetworkPacket(dst_addr, data_S[offset:(offset+div)], self.pktID, offset, frag)
                print('%s: sending packet "%s" on the out interface with mtu=%d' % (self, p, mtu))
                self.out_intf_L[0].put(p.to_byte_S())
                offset += div
        else:
            p = NetworkPacket(dst_addr, data_S)
            print('%s: sending packet "%s" on the out interface with mtu=%d' % (self, p, self.out_intf_L[0].mtu))
            self.out_intf_L[0].put(p.to_byte_S())  # send packets always enqueued successfully
        self.pktID += 1
    
    # receive packet from the network layer
    def udt_receive(self):
        pkt_S = self.in_intf_L[0].get()
        if pkt_S is not None:
            pkt = NetworkPacket.from_byte_S(pkt_S)
            if pkt.frag == 1:
                print('%s: received packet segment on the in interface' % (self))
                if pkt.offset == 0:
                    self.pkt = NetworkPacket(pkt.dst_addr, pkt.data_S, pkt.pkt_id, 0, 1)
                else:
                    self.pkt = NetworkPacket(pkt.dst_addr, (self.pkt.data_S + pkt.data_S), pkt.pkt_id, 0, 1)
            else:
                if self.pkt is not None:
                    self.pkt = NetworkPacket(pkt.dst_addr, (self.pkt.data_S + pkt.data_S), pkt.pkt_id, 0, 0)
                else:      
                    self.pkt = pkt                                
                print('%s: received packet "%s" on the in interface' % (self, self.pkt.to_byte_S()))
                self.pkt = None
    
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
    pktData = None
    # @param name: friendly router name for debugging
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
            mtu = self.out_intf_L[i].mtu
            pkt_S = None
            try:
                # get packet from interface i
                pkt_S = self.in_intf_L[i].get()
                # if packet exists make a forwarding decision
                if pkt_S is not None:
                    p = NetworkPacket.from_byte_S(pkt_S)  # parse a packet out

                    # HERE you will need to implement a lookup into the
                    # forwarding table to find the appropriate outgoing interface
                    # for now we assume the outgoing interface is also i

                    if(len(p) > mtu):
                        if(mtu <= NetworkPacket.header_len):
                            # print('%s: MTU on interface %d too small to transmit (mtu=%d)' % (self, i, mtu))
                            continue
                        pktID = p.pkt_id
                        offset = p.offset
                        frag = 1
                        dst_addr = p.dst_addr
                        self.pktData = p.data_S
                        div = mtu - (NetworkPacket.header_len)
                        numPkt = math.ceil(len(self.pktData)/div)
                        for j in range(0, numPkt):
                            if((p.frag == 0) and (j == (numPkt-1))):
                                frag = 0
                            fwdP = NetworkPacket(dst_addr, self.pktData[(div*(j)):(div*(j+1))], pktID, offset, frag)
                            print('%s: forwarding packet segment "%s" from interface %d to %d with mtu %d' % (self, fwdP, i, i, self.out_intf_L[i].mtu))
                            self.out_intf_L[i].put(fwdP.to_byte_S())
                            offset += div
                    print('%s: forwarding packet "%s" from interface %d to %d with mtu %d' \
                          % (self, p, i, i, self.out_intf_L[i].mtu))
                    self.out_intf_L[i].put(p.to_byte_S())
            except queue.Full:
                print('%s: packet "%s" lost on interface %d' % (self, p, i))
                pass
    
    # thread target for the host to keep forwarding data
    def run(self):
        print(threading.currentThread().getName() + ': Starting')
        while True:
            self.forward()
            if self.stop:
                print(threading.currentThread().getName() + ': Ending')
                return

# EOF