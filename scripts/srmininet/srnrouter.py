
import errno
import os

from ipmininet.router import Router
from ipmininet.router.config import BasicRouterConfig
from ipmininet.utils import realIntfList


class SRNConfig(BasicRouterConfig):

	def __init__(self, node, additional_daemons=(), *args, **kwargs):
		"""A simple router made of at least an OSPF daemon

		:param additional_daemons: Other daemons that should be used"""
		# Importing here to avoid circular import
		from ipmininet.router.config.ospf import OSPF
		from ipmininet.router.config.ospf6 import OSPF6
		from .config import SRNOSPF6, SRCtrl, SRDNSFwd
		# We don't want any zebra-specific settings, so we rely on the OSPF/OSPF6
		# DEPENDS list for that daemon to run it with default settings
		# We also don't want specific settings beside the defaults, so we don't
		# provide an instance but the class instead
		d = []
		if node.use_v4:
			d.append(OSPF)
		if node.use_v6:
			if self._node.controller:
				d.extend([SRNOSPF6, SRCtrl])
			else:
				d.append(OSPF6)
			if self._node.access_router:
				d.append(SRDNSFwd)
		d.extend(additional_daemons)
		super(BasicRouterConfig, self).__init__(node, daemons=d,
		                                        *args, **kwargs)

	def build(self):
		for intf in realIntfList(self._node):
			self.sysctl = "net.ipv6.conf.%s.seg6_enabled=1" % intf.name
		super(SRNConfig, self).build()


def mkdir_p(path):
	try:
		os.makedirs(path)
	except OSError as exc:
		if exc.errno == errno.EEXIST and os.path.isdir(path):
			pass
		else:
			raise


class SRNRouter(Router):
	def __init__(self, name, config=SRNConfig, controller=False,
	             access_router=False, sr_controller=None, cwd="/tmp", *args, **kwargs):
		self.controller = controller
		self.access_router = access_router
		self.sr_controller = sr_controller
		super(SRNRouter, self).__init__(name, config=config, cwd=cwd, *args, **kwargs)
		mkdir_p(cwd)
