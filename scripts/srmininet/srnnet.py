from mininet.log import lg as log

import ipaddress
from ipmininet.ipnet import IPNet, BroadcastDomain
from ipmininet.utils import L3Router, realIntfList, otherIntf

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
			for name, id in name_ospfid_mapping.iteritems():

				# Add host prefixes so that sr-ctrl can find the hosts in its computations
				prefix_list = [ipaddress.ip_interface(name_prefix_mapping[name].ip.compressed + "/64").network.with_prefixlen]  # FIXME temporary
				for itf in realIntfList(self[name]):
					if not L3Router.is_l3router_intf(otherIntf(itf)):
						for ip6 in itf.ip6s(exclude_lls=True):
							prefix_list.append(ipaddress.ip_interface(ip6.ip.compressed + "/64").network.with_prefixlen)  # FIXME temporary

				entry = {"routerName": name, "routerId" : id,
				         "addr": name_prefix_mapping[name].ip.compressed,
				         "prefix": ";".join(prefix_list),
				         "pbsid": name_prefix_mapping[name].ip.compressed + "/64"}  # FIXME temporary
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
					entry["routerId1"] = name_ospfid_mapping[entry["name1"]]
					entry["routerId2"] = name_ospfid_mapping[entry["name2"]]

					print(sr_controller_ovsdb.insert_entry("AvailableLink", entry))

	def buildFromTopo(self, topo):
		super(SRNNet, self).buildFromTopo(topo)
		# Add a loopback interface to each router
		for r in self.routers:
			lo = self.intf('lo', node=r, moveIntfFn=lambda x, y: True)
			lo.ip = '127.0.0.1/8'
			lo.ip6 = '::1'

	def _broadcast_domains(self):
		"""Build the broadcast domains for this topology"""
		domains = []
		interfaces = {intf: False
		              for n in self.values()
		              if BroadcastDomain.is_domain_boundary(n)
		              for intf in n.intfList()}
		for intf, explored in interfaces.iteritems():
			# the interface already belongs to a broadcast domain
			if explored:
				continue
			# create a new domain and explore the interface
			bd = BroadcastDomain(intf)
			# Mark all explored interfaces belonging to that domain
			for i in bd:
				interfaces[i] = True
				i.broadcast_domain = bd
			domains.append(bd)
		return domains
