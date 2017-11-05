from mininet.log import lg as log

import ipaddress
from ipmininet.ipnet import IPNet
from ipmininet.utils import L3Router

from .config import OVSDB, SRNOSPF6
from .srnhost import SRNHost
from .srnlink import SRNTCIntf
from .srnrouter import SRNConfig, SRNRouter


class SRNNet(IPNet):
	"""SRN-aware Mininet"""

	# TODO Setting the "intf" parameter here serves no purpose thanks to Mininet's code (=> propose a patch)
	def __init__(self,
	             router=SRNRouter,
	             intf=SRNTCIntf,
	             config=SRNConfig,
	             host=SRNHost,
	             *args, **kwargs):
		super(SRNNet, self).__init__(*args, router=router, intf=intf, use_v4=False, use_v6=True, config=config,
		                             host=host, **kwargs)

	def addLink(self, *args, **params):
		defaults = {"intf": self.intf}
		defaults.update(params)
		super(SRNNet, self).addLink(*args, **defaults)

	def start(self):
		# Controller nodes must be started first (because of ovsdb daemon)
		self.routers = sorted(self.routers, key=lambda router: not router.controller)

		super(SRNNet, self).start()

		# Enable SRv6 on all hosts
		for host in self.hosts:
			host.enable_srv6()

		# Insert the initial topology info to SRDB
		name_ospfid_mapping = {}
		sr_controller_ovsdb = None
		for router in self.routers:
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
			for name, id in name_ospfid_mapping.iteritems():
				print(sr_controller_ovsdb.insert_entry("NameIdMapping", {"routerName": name, "routerId": id}))

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
					entry["routerId1"] = name_ospfid_mapping[entry["name1"]]
					entry["routerId2"] = name_ospfid_mapping[entry["name2"]]

					print(sr_controller_ovsdb.insert_entry("AvailableLink", entry))
