#!/usr/bin/python

# FuZhou University, SDNLab
# Added by Chen, 2017.3.18

# Rewrite the topo.py to create an overlay network based on P4Switches.

#                  -> s2 <-
#                 /        \
#  ovs1 <--> s1 <-          -> s4 <--> ovs2
#                 \        /
#                  -> s3 <-

# Copyright 2013-present Barefoot Networks, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from mininet.net import Mininet, VERSION
from mininet.topo import Topo
from mininet.log import setLogLevel, info
from mininet.cli import CLI
from mininet.node import OVSController

from p4_mininet import P4Switch, P4Host

import argparse
from time import sleep
import os
import subprocess

_THIS_DIR = os.path.dirname(os.path.realpath(__file__))
_THRIFT_BASE_PORT = 22222

# Parsing Arguments

parser = argparse.ArgumentParser(description='Mininet demo')

parser.add_argument('--behavioral-exe', help='Path to behavioral executable',
                    type=str, action="store", required=True)
parser.add_argument('--json', help='Path to JSON config file',
                    type=str, action="store", required=True)
parser.add_argument('--cli', help='Path to BM CLI',
                    type=str, action="store", required=True)
parser.add_argument('--mode', choices=['l2', 'l3'], type=str, default='l3')

args = parser.parse_args()

# OvS Connections: host <--> ovsSwicth

# The hosts that connect to ovs1 or ovs2:
ovs1_host, ovs2_host = [], []

# Edge P4 Switches:
egsw = []

# Hosts:
hosts = []

class MyTopo(Topo):
    def __init__(self, sw_path, json_path, nb_hosts, nb_switches, links, nb_links, **opts):
        # Initialize topology and default options
        Topo.__init__(self, **opts)

        swes = []
        for i in xrange(nb_switches):
           sw = self.addSwitch('s%d' % (i + 1),
                               cls = P4Switch, # P4 Switch
                               sw_path = sw_path,
                               json_path = json_path,
                               thrift_port = _THRIFT_BASE_PORT + i,
                               pcap_dump = True,
                               device_id = i)
           if i == 0 or i == nb_switches-1:
               egsw.append(sw)
           swes.append(sw)

        for h in xrange(nb_hosts):
            hi = self.addHost('h%d' % (h+1)) 
            hosts.append(hi)
            if h < nb_hosts/2:
                ovs1_host.append(hi)
            else:
                ovs2_host.append(hi)
        
        port = 1
        for i, j in links:
            self.addLink(swes[i-1], swes[j-1], port1=port, port2=port)
            port = port+1

def HostConfig(net, nb_hosts):
    # Config the hosts by IP and MAC address
    for i in xrange(nb_hosts):
        print 'Config hosts h%d' % (i+1)
        obj = net.get(hosts[i])
        obj.setIP("10.0.0.%d" % (i+1))
        obj.setMAC("00:00:00:00:00:0%d" % (i+1))

def Connect(net, nb_hosts, nb_links):
    # Connect the overlay network to OvS network
    ovs1 = net.addSwitch('ovs1')
    ovs2 = net.addSwitch('ovs2')
    
    sw1 = net.get(egsw[0])
    sw2 = net.get(egsw[1])
    port = nb_links+1
    net.addLink(ovs1, sw1, port1=port, port2=port)
    net.addLink(ovs2, sw2, port1=port, port2=port)
    
    port = port+1    
    for h in ovs1_host:
        hi = net.get(h)
        net.addLink(ovs1, hi, port1 = port)
        port = port+1
    for h in ovs2_host:
        hi = net.get(h)
        net.addLink(ovs2, hi, port1 = port)
        port = port+1

def read_topo():
    nb_hosts = 0
    nb_switches = 0
    links = []
    nb_links = 0
    with open("topo.txt", "r") as f:
        line = f.readline()[:-1]
        w, nb_switches = line.split()
        assert(w == "switches")
        line = f.readline()[:-1]
        w, nb_hosts = line.split()
        assert(w == "hosts")
        for line in f:
            if not f: break
            a, b = line.split()
            a, b = int(a), int(b)
            links.append( (a, b) )
            nb_links = nb_links+1
    return int(nb_hosts), int(nb_switches), links, nb_links

def main():
    nb_hosts, nb_switches, links, nb_links = read_topo()
    
    mode = args.mode

    topo = MyTopo(args.behavioral_exe,
                  args.json,
                  nb_hosts, nb_switches, links, nb_links)

    net = Mininet(topo = topo,
                  controller = OVSController)
    
    # Connect the overlay network to the OvS switches at edge.
    Connect(net, nb_hosts, nb_links)
    
    # Config the hosts    
    print 'Config the hosts...\n'
    HostConfig(net, nb_hosts)    
    print '\nFinished, start the network...\n'

    net.start()
    
    for n in xrange(nb_hosts):
        h = net.get('h%d' % (n + 1))
        
	for off in ["rx", "tx", "sg"]:
            cmd = "/sbin/ethtool --offload eth0 %s off" % off
            print cmd
            h.cmd(cmd)
        
	print "disable ipv6"
        h.cmd("sysctl -w net.ipv6.conf.all.disable_ipv6=1")
        h.cmd("sysctl -w net.ipv6.conf.default.disable_ipv6=1")
        h.cmd("sysctl -w net.ipv6.conf.lo.disable_ipv6=1")
        h.cmd("sysctl -w net.ipv4.tcp_congestion_control=reno")
        h.cmd("iptables -I OUTPUT -p icmp --icmp-type destination-unreachable -j DROP")
	
	if mode == "l2":
            h.setDefaultRoute("dev eth0")
        else:
            h.setARP(sw_addr[n], sw_mac[n])
	    h.setDefaultRoute("dev eth0 via %s" % sw_addr[n])

    for n in xrange(nb_hosts):
        h = net.get('h%d' % (n + 1))
	# h.describe()

    sleep(1)

    print "Ready !"

    CLI( net )
    net.stop()

if __name__ == '__main__':
    setLogLevel( 'info' )
    main()
