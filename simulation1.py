# simulation1.py
import network1 as network
import link1 as link
import threading
from time import sleep
from rprint import print


# configuration parameters
router_queue_size = 0  # 0 means unlimited
# give the network sufficient time to transfer all packets before quitting
simulation_time = 2

if __name__ == '__main__':
    # keeps track of objects, so we can kill their threads
    object_L = []
    
    # create network nodes
    client = network.Host(1)
    object_L.append(client)
    server = network.Host(2)
    object_L.append(server)
    router_a = network.Router(name='A', intf_count=1, max_queue_size=router_queue_size)
    object_L.append(router_a)
    
    # create a Link Layer to keep track of links between network nodes
    link_layer = link.LinkLayer()
    object_L.append(link_layer)
    
    # add all the links
    # link parameters: from_node, from_intf_num, to_node, to_intf_num, mtu
    link_layer.add_link(link.Link(client, 0, router_a, 0, 50))
    link_layer.add_link(link.Link(router_a, 0, server, 0, 50))
    
    # start all the objects
    thread_L = [threading.Thread(name=object.__str__(), target=object.run) for object in object_L]
    for t in thread_L:
        t.start()
    
    # create some send events
    for i in range(3):
        client.udt_send(2, 'Sample data, Sample data, Sample data, Sample data, Sample data, Sample data, Sample data %d' % i)
    
    # give the network sufficient time to transfer all packets before quitting
    sleep(simulation_time)
    
    # join all threads
    for o in object_L:
        o.stop = True
    for t in thread_L:
        t.join()
    
    print("All simulation threads joined")

# EOF