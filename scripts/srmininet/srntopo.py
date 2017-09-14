
import os

from iptopo import IPTopo


class SRNTopo(IPTopo):

	def __init__(self, controllers, cwd=None, *args, **kwargs):
		""":param controllers: The name (or list of names) of routers that will run a SRN controller"""
		super(SRNTopo, self).__init__(*args, **kwargs)
		self.access_routers = []
		self.cwd = cwd

		self.controllers = controllers if not isinstance(controllers, basestring) else list(controllers)

	def addRouter(self, name, controller=False, **params):
		if self.cwd is not None and "cwd" not in params:
			params["cwd"] = os.path.join(self.cwd, name)
		super(SRNTopo, self).addRouter(name, controller=controller, **params)

	def addLink(self, node1, node2, **opts):

		# FIXME Does not work with a switch between two routers
		access_router = None
		if self.isRouter(node1) and not self.isRouter(node2):
			access_router = node1
		elif not self.isRouter(node1) and self.isRouter(node2):
			access_router = node2

		if access_router:
			self.getNodeInfo(access_router, access_router, True)

		super(SRNTopo, self).addLink(node1, node2, **opts)
