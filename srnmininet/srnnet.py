from mininet.log import lg as log

import ipaddress
from mininet.node import Switch
from ipmininet.utils import L3Router, otherIntf, realIntfList
from sr6mininet.sr6host import SR6Host
from sr6mininet.sr6link import SR6TCIntf
from sr6mininet.sr6net import SR6Net

from .config import OVSDB, SRNOSPF6
from .srnrouter import SRNConfig, SRNRouter


class SRNNet(SR6Net):
    """SRN-aware Mininet"""

    def __init__(self,
                 router=SRNRouter,
                 intf=SR6TCIntf,
                 config=SRNConfig,
                 host=SR6Host,
                 static_routing=False,
                 *args, **kwargs):
        super(SRNNet, self).__init__(*args, router=router, intf=intf, config=config,
                                     host=host, static_routing=static_routing, **kwargs)

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
        to_visit = [(start, 0, None)]
        # Explore all interfaces in broadcast domain recursively, until we find the 'end' interface
        while to_visit:
            i, i_delay, i_bw = to_visit.pop(0)
            if i in visited:
                continue
            visited.add(i)
            n = otherIntf(i)
            n_delay = i_delay + int(i.delay.split("ms")[0])
            n_bw = min(i_bw, i.bw) if i_bw is not None else i.bw
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
                 "addr1": str(intf1.ip6s(exclude_lls=True).next().ip),
                 # Can raise an exception if none exists
                 "addr2": str(intf2.ip6s(exclude_lls=True).next().ip),
                 # Can raise an exception if none exists
                 "metric": intf1.igp_metric,
                 "bw": bw,
                 "ava_bw": intf1.bw,
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

        super(SRNNet, self).start()

        # Insert the initial topology info to SRDB
        name_ospfid_mapping = {}
        name_prefix_mapping = {}
        sr_controller_ovsdb = None
        for router in self.routers:
            for ip6 in self[router.name].intf("lo").ip6s(exclude_lls=True):
                if ip6 != ipaddress.ip_interface("::1"):
                    name_prefix_mapping[router.name] = ip6
                    break
            for daemon in router.config.daemons:
                if daemon.NAME == SRNOSPF6.NAME:
                    if daemon.options.routerid:
                        name_ospfid_mapping[router.name] = daemon.options.routerid
                    else:
                        name_ospfid_mapping[router.name] = router.config.routerid
                    name_ospfid_mapping[router.name] = int(ipaddress.ip_address(name_ospfid_mapping[router.name]))
                elif daemon.NAME == OVSDB.NAME:
                    sr_controller_ovsdb = daemon

        if sr_controller_ovsdb:
            log.info('*** Inserting mapping between names and ids to OVSDB\n')
            for r in self.routers:
                print(sr_controller_ovsdb.insert_entry(*self.ovsdb_node_entry(r, name_ospfid_mapping.get(r.name, None),
                                                                              name_prefix_mapping[r.name])))

            log.info('*** Inserting mapping between links, router ids and ipv6 addresses to OVSDB\n')
            for domain in self.broadcast_domains:
                if len(domain.routers) <= 1:
                    continue
                for intf_r1 in list(domain.routers):
                    for intf_r2 in list(domain.routers):
                        if intf_r1.name <= intf_r2.name:
                            continue
                        # TODO Links should be oriented in the future !
                        print(sr_controller_ovsdb.insert_entry(
                            *self.ovsdb_link_entry(intf_r1, intf_r2,
                                                   name_ospfid_mapping.get(intf_r1.node.name, None),
                                                   name_ospfid_mapping.get(intf_r2.node.name, None))))

        log.info('*** Individual daemon commands with netns commands\n')
        for r in self.routers:
            for d in r.config.daemons:
                log.info('ip netns exec %s "%s"\n' % (r.name, d.startup_line))
