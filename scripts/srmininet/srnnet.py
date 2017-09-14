
from ipmininet.ipnet import IPNet

from .srnlink import SRNTCIntf
from .srnrouter import SRNRouter, SRNConfig


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
