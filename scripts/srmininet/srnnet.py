
import json
from mininet.log import lg as log

import ipaddress
from ipmininet.ipnet import IPNet

from .config import OVSDB, SRNOSPF6
from .srnlink import SRNTCIntf
from .srnrouter import SRNConfig, SRNRouter


class SRNNet(IPNet):
	"""SRN-aware Mininet"""

	# TODO Setting the "intf" parameter here serves no purpose thanks to Mininet's code (=> propose a patch)
	def __init__(self,
	             router=SRNRouter,
	             intf=SRNTCIntf,
	             config=SRNConfig,
	             *args, **kwargs):
		super(SRNNet, self).__init__(*args, router=router, intf=intf, use_v4=False, use_v6=True, config=config, **kwargs)

	def addLink(self, *args, **params):
		defaults = {"intf": self.intf}
		defaults.update(params)
		super(SRNNet, self).addLink(*args, **defaults)

	def start(self):
		# Controller nodes must be started first (because of ovsdb daemon)
		self.routers = sorted(self.routers, key=lambda router: not router.controller)

		super(SRNNet, self).start()

		# Add mapping between router ids and names to ovsdb database
		name_ospfid_mapping = {}
		sr_controller = None
		for router in self.routers:
			if router.controller:
				sr_controller = router
			for daemon in router.config.daemons:
				if daemon.NAME == SRNOSPF6.NAME:
					if daemon.options.routerid:
						name_ospfid_mapping[router.name] = daemon.options.routerid
					else:
						name_ospfid_mapping[router.name] = router.config.routerid
					name_ospfid_mapping[router.name] = int(ipaddress.ip_address(name_ospfid_mapping[router.name]))
					break

		if sr_controller:
			log.info('*** Inserting mapping between names and ids to OVSDB\n')
			for name, id in name_ospfid_mapping.iteritems():
				print(self.insertNameIdMapping(sr_controller, name, id))

	@staticmethod
	def insertNameIdMapping(sr_controller, name, id):
		insert = OVSDB.OVSDB_INSERT_FORMAT % ("SR_test",json.dumps({"routerName": name, "routerId": id}), "NameIdMapping")
		return sr_controller.cmd("ovsdb-client transact tcp:[::1]:6640 '%s'" % insert)
