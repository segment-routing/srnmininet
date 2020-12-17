import heapq
import ipaddress
import time

from ipmininet.ipnet import IPNet
from ipmininet.utils import L3Router, otherIntf, realIntfList
from mininet.log import lg as log
from mininet.node import Switch

from .config import OVSDB, SRNOSPF6
from .link import SRNIntf
from .srnhost import SRNHost
from .srnrouter import SRNConfig, SRNRouter


class SRNNet(IPNet):
    """SRN-aware Mininet"""

    def __init__(self,
                 router=SRNRouter,
                 intf=SRNIntf,
                 config=SRNConfig,
                 host=SRNHost,
                 static_routing=False,
                 try_route_timeout=4,
                 *args, **kwargs):
        self.static_routing = static_routing
        self.try_route_timeout = try_route_timeout
        super().__init__(*args, router=router, intf=intf, config=config, host=host, use_v4=False, use_v6=True, **kwargs)

    def addRouter(self, name, cls=None, **params):
        params["static_routing"] = self.static_routing
        super().addRouter(name, cls, **params)

    def _try_add_route(self, node, cmd):
        """Try for some time to insert the route
           If addition is tried directly, the operation is likely to fail."""
        out = node.cmd(cmd)
        step = 10
        for i in range(0, self.try_route_timeout * 1000, step):
            if len(out) == 0:
                return out
            time.sleep(step / 1000.)
            out = node.cmd(cmd)
        return out

    def _add_static_routes_to_itf(self, r, dest, routes):
        """Add static the "routes" between "r" and "dest_itf" as an IGP protocol would do."""
        dest_itf = routes[0][1]  # dest_itfs in routes are all on the same LAN and thus have the same prefixes
        for ip6 in dest_itf.ip6s(exclude_lls=True, exclude_lbs=True):
            dest_prefix = ip6.network.with_prefixlen

            if len(routes) == 1:
                cost, _, direct_peer_itf = routes[0]
                if ipaddress.ip_address(direct_peer_itf.ip6) in ipaddress.ip_network(dest_prefix):
                    continue  # Already a route for this prefix
                cmd = ["ip", "-6", "route", "add", dest_prefix,
                       "via", direct_peer_itf.ip6, "metric", str(cost)]
                out = self._try_add_route(r, cmd)
                if len(out) > 0:
                    log.error("Route from %s to %s<%s>: " % (r.name, dest, dest_itf.name) + " ".join(cmd) + "\n")
                    log.error(out)
            elif len(routes) > 0:
                cmd = ["ip", "-6", "route", "add", dest_prefix, "metric", str(routes[0][0])]
                for cost, _, direct_peer_itf in routes:
                    if ipaddress.ip_address(direct_peer_itf.ip6) in ipaddress.ip_network(dest_prefix):
                        continue  # Already a route for this prefix
                    cmd.extend(["nexthop", "via", direct_peer_itf.ip6, "weight", "1"])
                out = self._try_add_route(r, cmd)
                if len(out) > 0:
                    log.error("Route from %s to %s<%s>: " % (r.name, dest, dest_itf.name) + " ".join(cmd) + "\n")
                    log.error(out)

    def ovsdb_node_entry(self, r, ospfv3_id, prefix):
        """
        This function formats the OVSDB entry to install so that the controller is aware of a router.

        :param r: The router to insert an entry for
        :param ospfv3_id: The OSPFv3 router id
        :param prefix: The prefix of the loopback address of this router
        :return: The tuple (ovsdb table name, entry to insert)
        """

        # Add host prefixes so that sr-ctrl can find the hosts in its computations
        prefix_list = [prefix.network.with_prefixlen]
        for itf in realIntfList(self[r.name]):
            if not L3Router.is_l3router_intf(otherIntf(itf)):
                for ip6 in itf.ip6s(exclude_lls=True):
                    prefix_list.append(ip6.network.with_prefixlen)

        entry = {"routerName": r.name, "routerId": ospfv3_id,
                 "addr": prefix.ip.compressed,
                 "prefix": ";".join(prefix_list),
                 "pbsid": prefix.network.with_prefixlen}
        if self.static_routing:
            entry["name"] = entry["routerName"]
            del entry["routerId"]
            del entry["routerName"]
            return "NodeState", entry
        else:
            return "NameIdMapping", entry

    @staticmethod
    def find_path_properties(start, end):
        """Find the path properties (delay and bandwidth) of the path between the interfaces of the routers
           assuming that they are in the same broadcast domain.
           Note: This does not handle loops inside the broadcast domain.
           For that, we would need to pre-compute STP"""

        visited = set()
        to_visit = [(start, 0, 0)]
        # Explore all interfaces in broadcast domain recursively, until we find the 'end' interface
        while to_visit:
            i, i_delay, i_bw = to_visit.pop(0)
            if i in visited:
                continue
            visited.add(i)
            n = otherIntf(i)
            n_delay = i_delay + int(i.delay.split("ms")[0])
            if i_bw == 0:  # 0 means no bandwidth limit
                n_bw = i.bw
            elif i.bw != 0:
                n_bw = min(i_bw, i.bw)
            else:
                n_bw = i_bw
            if isinstance(n.node, Switch):  # Expand
                for s_i in realIntfList(n.node):
                    to_visit.append((s_i, i_delay + n_delay, n_bw))
            elif n.name == end.name:
                return n_delay, n_bw
        return None, None

    def ovsdb_link_entry(self, intf1, intf2, ospfv3_id1, ospfv3_id2):
        """
        This function formats the OVSDB entry to install so that the controller is aware of a link.

        :param intf1: The interface on the first router in the broadcast domain
        :param intf2: The other interface of the router in the broadcast domain
        :param ospfv3_id1: The OSPFv3 router id of link.intf1.node
        :param ospfv3_id2: The OSPFv3 router id of link.intf2.node
        :return: The tuple (ovsdb table name, entry to insert)
        """
        ms_delay, bw = self.find_path_properties(start=intf1, end=intf2)
        entry = {"name1": intf1.node.name, "name2": intf2.node.name,
                 "addr1": str(next(intf1.ip6s(exclude_lls=True)).ip),
                 # Can raise an exception if none exists
                 "addr2": str(next(intf2.ip6s(exclude_lls=True)).ip),
                 # Can raise an exception if none exists
                 "metric": intf1.igp_metric,
                 "bw": bw,
                 "ava_bw": bw,
                 "delay": ms_delay}
        if self.static_routing:
            return "LinkState", entry
        else:
            entry["routerId1"] = ospfv3_id1
            entry["routerId2"] = ospfv3_id2
            return "AvailableLink", entry

    def start(self):
        # Controller nodes must be started first (because of ovsdb daemon)
        self.routers = sorted(self.routers, key=lambda router: not router.controller)

        if self.static_routing:
            log.output("*** Inserting static routes\n")
            for r in self.routers:
                lans, loopbacks = find_closest_paths(r)
                for lan, routes in lans.items():
                    self._add_static_routes_to_itf(r, lan, routes)
                for node, routes in loopbacks.items():
                    self._add_static_routes_to_itf(r, node, routes)

        super().start()

        # Insert the initial topology info to SRDB
        name_ospfid_mapping = {}
        name_prefix_mapping = {}
        sr_controller_ovsdb = None
        for router in self.routers:
            for ip6 in self[router.name].intf("lo").ip6s(exclude_lls=True, exclude_lbs=True):
                name_prefix_mapping[router.name] = ip6
                break
            for daemon in router.nconfig.daemons:
                if daemon.NAME == SRNOSPF6.NAME:
                    if daemon.options.routerid:
                        name_ospfid_mapping[router.name] = daemon.options.routerid
                    else:
                        name_ospfid_mapping[router.name] = \
                            router.nconfig.routerid
                    name_ospfid_mapping[router.name] = int(ipaddress.ip_address(name_ospfid_mapping[router.name]))
                elif daemon.NAME == OVSDB.NAME:
                    sr_controller_ovsdb = daemon

        if sr_controller_ovsdb:
            log.info('*** Inserting mapping between names and ids to OVSDB\n')
            for r in self.routers:
                print(sr_controller_ovsdb.insert_entry(*self.ovsdb_node_entry(r, name_ospfid_mapping.get(r.name, None),
                                                                              name_prefix_mapping[r.name])))

            log.info('*** Inserting mapping between links, router ids and ipv6 addresses to OVSDB\n')
            print(len(self.broadcast_domains))
            for domain in self.broadcast_domains:
                print(domain.interfaces)
                if len(domain.routers) <= 1:
                    continue
                print(len(domain.routers))
                for intf_r1 in list(domain.routers):
                    for intf_r2 in list(domain.routers):
                        if intf_r1.name <= intf_r2.name:
                            continue
                        print(intf_r1.name)
                        print(intf_r2.name)
                        # TODO Links should be oriented in the future !
                        print(sr_controller_ovsdb.insert_entry(
                            *self.ovsdb_link_entry(intf_r1, intf_r2,
                                                   name_ospfid_mapping.get(intf_r1.node.name, None),
                                                   name_ospfid_mapping.get(intf_r2.node.name, None))))

        log.info('*** Individual daemon commands with netns commands\n')
        for r in self.routers:
            for d in r.nconfig.daemons:
                log.info('ip netns exec %s "%s"\n' % (r.name, d.startup_line))


def cost_intf(intf):
    return intf.igp_metric


def find_closest_paths(base):
    """Find the dict {router: [(path_cost, direct_peer_itf)]} for a minimum path_cost for each router
       and the dict {(host, host_itf): [(path_cost, direct_peer_itf)]} for a minimum path_cost for each interface of an host.
       It takes into account ECMP paths."""
    visited = set()
    to_visit = [(cost_intf(intf), intf, None) for intf in realIntfList(base)]
    heapq.heapify(to_visit)
    lans = {}
    loopbacks = {}

    # Explore all interfaces in base ASN recursively
    while to_visit:
        cost, intf, direct_next_itf = heapq.heappop(to_visit)
        visited.add(intf.name)
        for peer_intf in intf.broadcast_domain:
            if peer_intf.node.name == base.name or peer_intf.name == intf.name:
                continue

            # Update path to LANs
            destination = frozenset(intf.broadcast_domain.interfaces)

            min_paths = lans.get(destination, None)
            if not min_paths or min_paths[0][0] > cost:
                lans[destination] = [(cost, peer_intf, direct_next_itf if direct_next_itf else peer_intf)]
            elif min_paths[0][0] == cost:  # ECMP
                found = False
                for path in min_paths:
                    if path[2].name == direct_next_itf.name:
                        found = True
                        break
                if not found:
                    min_paths.append((cost, peer_intf, direct_next_itf if direct_next_itf else peer_intf))

            # Update path to loopbacks
            if L3Router.is_l3router_intf(peer_intf):
                peer = peer_intf.node.name
                lo_itf = peer_intf.node.intf("lo")
                lo_min_paths = loopbacks.get(peer, None)

                if not lo_min_paths or lo_min_paths[0][0] > cost:
                    loopbacks[peer] = [(cost, lo_itf, direct_next_itf if direct_next_itf else peer_intf)]
                elif lo_min_paths[0][0] == cost:  # ECMP
                    found = False
                    for path in lo_min_paths:
                        if path[2].name == direct_next_itf.name:
                            found = True
                            break
                    if not found:
                        lo_min_paths.append((cost, lo_itf, direct_next_itf if direct_next_itf else peer_intf))

            # Hosts don't forward packets
            if L3Router.is_l3router_intf(peer_intf):
                for x in realIntfList(peer_intf.node):
                    if x.name != peer_intf.name and x.name not in visited:
                        heapq.heappush(to_visit,
                                       (cost + cost_intf(x), x, direct_next_itf if direct_next_itf else peer_intf))

    # Add routes to loopbacks, i.e., the route with the shortest path to a lan of the node

    return lans, loopbacks
