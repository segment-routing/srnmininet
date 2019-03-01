import argparse
import datetime
import json
import os
import time
from mininet.log import LEVELS, lg

import ipmininet
import psutil
from ipmininet.utils import realIntfList
from sr6mininet.cli import SR6CLI

from srnmininet.albilene import Albilene
from srnmininet.config.config import SRDNSProxy, SRRouted
from srnmininet.square_axa import SquareAxA
from srnmininet.srnnet import SRNNet
from srnmininet.utils import daemon_in_node

components = ["sr-ctrl", "sr-routed", "sr-dnsproxy", "sr-nsd"]


# Argument parsing

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--log', choices=LEVELS.keys(), default='info',
                        help='The level of details in the logs.')
    parser.add_argument('--log-dir', help='Logging directory root',
                        default='/tmp/logs-%s' % datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S'))
    parser.add_argument('--src-dir', help='Source directory root of SR components',
                        default='srn')
    return parser.parse_args()


def test_dns_latency(link_delay):
    topo_args = {"schema_tables": full_schema["tables"],
                 "cwd": args.log_dir,
                 "link_delay": link_delay}
    net = SRNNet(topo=SquareAxA(**topo_args), static_routing=True)
    try:
        net.start()

        client = net["client"]
        server = net["server"]
        dns_proxy_ip6 = None
        for node in net.routers:
            if daemon_in_node(node, SRDNSProxy) is not None:
                for itf in node.intfList():
                    for ip6 in itf.ip6s(exclude_lls=True):
                        if ip6.ip.compressed != "::1":
                            dns_proxy_ip6 = ip6.ip.compressed
                            lg.debug("SRDNSProxy address found was %s", dns_proxy_ip6)
        if dns_proxy_ip6 is None:
            raise Exception("Cannot find a global address for a node with SRDNSProxy")

        time.sleep(10)
        cmd = [sr_testdns, "sr", "100", server.name + ".test.sr", dns_proxy_ip6]
        out = client.cmd(cmd)
        with open(os.path.join(args.log_dir, "sr-testdns-5ms-rtt.log"), "w") as fileobj:
            fileobj.write(str(out))
    finally:
        net.stop()


def map_pings_to_segments(source_node, destination_node, access_router):
    dest_node_ip6 = None
    for itf in realIntfList(destination_node):
        for ip6 in itf.ip6s(exclude_lls=True):
            dest_node_ip6 = ip6.ip.compressed
            lg.debug("server address found was %s", dest_node_ip6)
    if dest_node_ip6 is None:
        raise Exception("Cannot find a global address for the server")

    routed = daemon_in_node(access_router, SRRouted)
    cmd = ["ip", "-6", "route", "show", "table", routed.localsid_name]
    out = access_router.cmd(cmd)
    lines = out.split("\n")
    if len(lines) == 0:
        raise Exception("Cannot find an encap rule in the %s of %s" % (routed.localsid_name, access_router.name))
    bsid = lines[0].split(" ")[0]
    print(lines[0])

    cmd = ["ip", "-6", "route", "add", dest_node_ip6, "encap", "seg6", "mode", "inline", "segs", bsid,
           "dev", realIntfList(source_node)[0].name]
    print(" ".join(cmd))
    out = source_node.cmd(cmd)
    print(out)

    return dest_node_ip6


def wait_access_router_start(node):

    cmd = ["pgrep", "sr-routed"]
    out = node.cmd(cmd)
    pids = out.split("\n")
    pids = [int(pid[:-1]) for pid in pids if len(pid) > 0]
    if len(pids) == 0:
        raise Exception("Cannot find sr-routed daemon")

    for pid in pids:
        p = psutil.Process(pid)
        old_percentage = 100.0
        while True:
            percentage = p.cpu_percent(1)
            if percentage < 20.0 and old_percentage < 20.0:
                break
            old_percentage = percentage
            time.sleep(1)


def test_flapping_link():
    topo_args = {"schema_tables": full_schema["tables"], "cwd": args.log_dir}
    net = SRNNet(topo=Albilene(**topo_args))
    try:
        net.start()

        # Create a binding segment
        client = net["client"]
        server = net["server"]
        dns_proxy_ip6 = None
        for node in net.routers:
            if daemon_in_node(node, SRDNSProxy) is not None:
                for itf in node.intfList():
                    for ip6 in itf.ip6s(exclude_lls=True):
                        if ip6.ip.compressed != "::1":
                            dns_proxy_ip6 = ip6.ip.compressed
                            lg.debug("SRDNSProxy address found was %s", dns_proxy_ip6)
        if dns_proxy_ip6 is None:
            raise Exception("Cannot find a global address for a node with SRDNSProxy")

        # Wait for IGP convergence
        wait_access_router_start(client)

        time.sleep(10)
        cmd = [sr_testdns, "-d", "8", "sr", "1", server.name + ".test.sr", dns_proxy_ip6]
        print(" ".join(cmd))
        out = client.cmd(cmd)
        print(out)

        server_ip6 = map_pings_to_segments(client, server, net["A"])

        # Return path

        cmd = [sr_testdns, "-d", "8", "sr", "1", client.name + ".test.sr", dns_proxy_ip6]
        print(" ".join(cmd))
        out = server.cmd(cmd)
        print(out)

        map_pings_to_segments(server, client, net["F"])

        print("*** Route was inserted")
        SR6CLI(net)

        print("** Using 'ping6 %s' to test the discovered path **" % server_ip6)
        cmd = ["ping6", "-c", "5", server_ip6]
        out = client.cmd(cmd)
        print(out)

        # Make a link fail
        cmd = ["ip", "link", "set", "B-eth0", "down"]
        out = net["B"].cmd(cmd)
        print(out)
        print("*** The link A-B failed")
        SR6CLI(net)

        print("** Using 'ping6 %s' to test after failure **" % server_ip6)
        cmd = ["ping6", "-c", "5", server_ip6]
        out = client.cmd(cmd)
        print(out)

        # Bring the link back up
        cmd = ["ip", "link", "set", "B-eth0", "up"]
        net["B"].cmd(cmd)
        cmd = ["ip", "-6", "addr", "add", next(net["B"].intf("B-eth0").ip6s(exclude_lls=True)), "dev", "B-eth0"]
        net["B"].cmd(cmd)
        print("*** The link A-B is back up")
        SR6CLI(net)

        print("** Using 'ping6 %s' to test the path when back up **" % server_ip6)
        cmd = ["ping6", "-c", "5", server_ip6]
        out = client.cmd(cmd)
        print(out)

    finally:
        net.stop()


args = parse_args()

with open(os.path.join(args.src_dir, "sr.ovsschema"), "r") as fileobj:
    full_schema = json.load(fileobj)

lg.setLogLevel(args.log)
if args.log == 'debug':
    ipmininet.DEBUG_FLAG = True
sr_testdns = os.path.join(os.path.abspath(args.src_dir), "bin", "sr-testdns")

# Add SR components to PATH
os.environ["PATH"] += os.pathsep + os.path.join(os.path.abspath(args.src_dir), "bin")

# Give the database description to the topology
test_dns_latency("1ms")

# Flapping link
test_flapping_link()
