import string

from .config import SRCtrlDomain
from .srntopo import SRNTopo


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

    def __init__(self, controller_idx=2, square_size=3, schema_tables=None,
                 link_delay="1ms", link_bandwidth=100, *args, **kwargs):
        """:param controller_idx: The index of routers that will run the SR controller
           :param square_size: The size of the squares of routers (> 0)
           :param link_delay: The link delay
           :param link_bandwidth: The link bandwidth"""

        self.link_delay = link_delay
        self.square_size = square_size
        self.link_bandwidth = link_bandwidth

        if self.square_size <= 0:
            raise Exception("Negative square size for %s" % type(self).__name__)
        elif controller_idx <= 0 or controller_idx >= self.square_size * self.square_size:
            raise Exception("Negative or too big index for the router hosting the controller"
                            + "(square size %d, index %s) for %s"
                            % (self.square_size, controller_idx, type(self).__name__))

        char_list = list(string.ascii_uppercase)
        self.grid = char_list
        loop_alphabet = 2
        while len(self.grid) < self.square_size ** 2:
            self.grid.extend([char * loop_alphabet for char in char_list])
            loop_alphabet += 1
        del self.grid[self.square_size ** 2:]

        controller = self.grid[controller_idx]
        self.schema_tables = schema_tables if schema_tables else {}

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

        self.addOverlay(SRCtrlDomain(access_routers=(self.grid[0],),
                                     sr_controller=self.controllers[0], schema_tables=self.schema_tables))

        super(SquareAxA, self).build(*args, **kwargs)

    def addLink(self, node1, node2, **opts):

        default_params1 = {"bw": self.link_bandwidth, "delay": self.link_delay}
        default_params1.update(opts.get("params1", {}))
        opts["params1"] = default_params1

        default_params2 = {"bw": self.link_bandwidth, "delay": self.link_delay}
        default_params2.update(opts.get("params2", {}))
        opts["params2"] = default_params2

        super(SRNTopo, self).addLink(node1, node2, **opts)
