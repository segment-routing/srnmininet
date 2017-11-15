from mininet.log import lg as log

import ipaddress
from ipmininet.utils import L3Router, otherIntf, realIntfList
from sr6mininet.sr6host import SR6Host
from sr6mininet.sr6net import SR6Net

from .config import OVSDB, SRNOSPF6
from .srnlink import SRNTCIntf
from .srnrouter import SRNConfig, SRNRouter


class SRNNet(SR6Net):
	"""SRN-aware Mininet"""

	# TODO Setting the "intf" parameter here serves no purpose thanks to Mininet's code (=> propose a patch)
	def __init__(self,
	             router=SRNRouter,
	             intf=SRNTCIntf,
	             config=SRNConfig,
	             host=SR6Host,
	             static_routing=False,  # Not starting quagga daemons
	             *args, **kwargs):
		super(SRNNet, self).__init__(*args, router=router, intf=intf, config=config,
		                             host=host, static_routing=static_routing, **kwargs)

	def addLink(self, *args, **params):
		defaults = {"intf": self.intf}
		defaults.update(params)
		super(SRNNet, self).addLink(*args, **defaults)

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
				name = r.name
				id = name_ospfid_mapping.get(name, None)

				# Add host prefixes so that sr-ctrl can find the hosts in its computations
				prefix_list = [ipaddress.ip_interface(name_prefix_mapping[name].ip.compressed + "/64").network.with_prefixlen]  # FIXME temporary
				for itf in realIntfList(self[name]):
					if not L3Router.is_l3router_intf(otherIntf(itf)):
						for ip6 in itf.ip6s(exclude_lls=True):
							prefix_list.append(ipaddress.ip_interface(ip6.ip.compressed + "/64").network.with_prefixlen)  # FIXME temporary

				entry = {"routerName": name, "routerId": id,
				         "addr": name_prefix_mapping[name].ip.compressed,
				         "prefix": ";".join(prefix_list),
				         "pbsid": name_prefix_mapping[name].ip.compressed + "/64"}  # FIXME temporary
				if self.static_routing:
					entry["name"] = entry["routerName"]
					del entry["routerId"]
					del entry["routerName"]
					print(sr_controller_ovsdb.insert_entry("NodeState", entry))
				else:
					print(sr_controller_ovsdb.insert_entry("NameIdMapping", entry))

			log.info('*** Inserting mapping between links, router ids and ipv6 addresses to OVSDB\n')
			for link in self.links:
				if L3Router.is_l3router_intf(link.intf1) and L3Router.is_l3router_intf(link.intf2):

					# TODO Links should be oriented in the future !
					entry = {"name1": link.intf1.node.name, "name2": link.intf2.node.name,
					         "addr1": str(link.intf1.ip6s(exclude_lls=True).next().ip),  # Can raise an exception if none exists
					         "addr2": str(link.intf2.ip6s(exclude_lls=True).next().ip),  # Can raise an exception if none exists
					         "metric": link.intf1.igp_metric,
					         "bw": link.intf1.bw,
					         "ava_bw": link.intf1.bw,
					         "delay": link.intf1.delay}
					if self.static_routing:
						print(sr_controller_ovsdb.insert_entry("LinkState", entry))
					else:
						entry["routerId1"] = name_ospfid_mapping[entry["name1"]]
						entry["routerId2"] = name_ospfid_mapping[entry["name2"]]
						print(sr_controller_ovsdb.insert_entry("AvailableLink", entry))

		log.info('*** Individual daemon commands with netns commands\n')
		for r in self.routers:
			for d in r.config.daemons:
				log.info('ip netns exec %s "%s"\n' % (r.name, d.startup_line))
