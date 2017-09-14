
import string

from .srntopo import SRNTopo
from .config import SRCtrlDomain


class SquareAxA(SRNTopo):
	"""
		client --- A --- B --- C
				   |     |	   |
				   D --- E --- F
				   |	 |	   |
				   G --- H --- I --- server

	client and server represents two hosts
	In this example, self.square_size == 3
	"""

	def __init__(self, controller_idx=3, square_size=3, *args, **kwargs):
		""":param controller_idx: The index of routers that will run the SR controller
		   :param square_size: The size of the squares of routers (> 0)"""

		self.square_size = square_size

		if self.square_size <= 0:
			raise Exception("Negative square size for %s" % type(self).__name__)
		elif controller_idx <= 0 or controller_idx < self.square_size:
			raise Exception("Negative or too big index for the router hosting the controller"
			                + "(square size %d, index %s) for %s"
			                % (self.square_size, controller_idx, type(self).__name__))

		char_list = list(string.ascii_uppercase)
		self.grid = char_list
		loop_alphabet = 2
		while len(self.grid) < self.square_size**2:
			self.grid.extend([char * loop_alphabet for char in char_list])
			loop_alphabet += 1
		del self.grid[self.square_size**2:]

		controller = self.grid[controller_idx]

		super(SquareAxA, self).__init__(controller, *args, **kwargs)

	def build(self, *args, **kwargs):

		for router in self.grid:
			controller = router in self.controllers
			self.addRouter(router, controller=controller)

		for i in range(self.square_size):
			for j in range(self.square_size):
				idx = i * self.square_size + j
				if j != self.square_size - 1:
					self.addLink(self.grid[idx], self.grid[idx + 1])
				if i != self.square_size - 1:
					self.addLink(self.grid[idx], self.grid[idx + self.square_size])

		client = self.addHost("client")
		server = self.addHost("server")
		self.addLink(self.grid[0], client)
		self.addLink(self.grid[-1], server)

		self.addOverlay(SRCtrlDomain(access_routers=(self.grid[0], self.grid[-1]), sr_controller=self.controllers[0]))

	def addLink(self, node1, node2, **opts):

		default_params1 = {"bw": 100, "delay": 1.00}
		default_params1.update(opts.get("params1", {}))
		opts["params1"] = default_params1

		default_params2 = {"bw": 100, "delay": 1.00}
		default_params2.update(opts.get("params2", {}))
		opts["params2"] = default_params2

		super(SRNTopo, self).addLink(node1, node2, **opts)
