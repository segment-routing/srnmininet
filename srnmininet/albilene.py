from .config import SRCtrlDomain
from .srntopo import SRNTopo


class Albilene(SRNTopo):
    """
                                     +---+
                       +-------------+ B +-------------+
                       |             +---+             |
                       |                               |
        +--------+   +-+-+   +---+   +---+   +---+   +-+-+   +--------+
        | client +---+ A +---+ C +---+ D +---+ E +---+ F +---+ server |
        +--------+   +---+   +-+-+   +---+   +-+-+   +---+   +--------+
                             | |               |
                             | |      5ms      |
                             | +---------------+
                             |
                       +-----+------+
                       | controller |
                       +------------+

    Client and server represents two hosts, the other are routers.
    All the links have an IGP weight of 1.
    Link latencies are set at 1ms except for the latency of (C, E) which has a latency of 5ms.
    """

    def __init__(self, schema_tables=None, link_bandwidth=100, *args, **kwargs):
        """:param schema_tables: The schema table of ovsdb
           :param link_bandwidth: The link bandwidth"""
        self.link_delay = "1ms"
        self.link_bandwidth = link_bandwidth
        self.schema_tables = schema_tables if schema_tables else {}

        super().__init__("controller", *args, **kwargs)

    def build(self, *args, **kwargs):

        # Controllers
        controller = self.addRouter(self.controllers[0])

        # Routers
        a = self.addRouter("A")
        b = self.addRouter("B")
        c = self.addRouter("C")
        d = self.addRouter("D")
        e = self.addRouter("E")
        f = self.addRouter("F")

        # Hosts
        client = self.addHost("client")
        server = self.addHost("server")

        # Links
        self.addLink(a, b)
        self.addLink(c, controller)
        self.addLink(client, a)
        self.addLink(a, c)
        self.addLink(c, d)
        self.addLink(d, e)
        self.addLink(c, e, delay="5ms")
        self.addLink(e, f)
        self.addLink(f, server)
        self.addLink(b, f)

        # SRN overlay
        self.addOverlay(SRCtrlDomain(access_routers=(a, f), sr_controller=controller, schema_tables=self.schema_tables,
                                     hosts=self.hosts()))

        super().build(*args, **kwargs)

    def addRouter(self, name, **params):
        return super().addRouter(name, **params)

    def addLink(self, node1, node2, delay=None, **opts):
        delay = self.link_delay if delay is None else delay
        return super().addLink(node1, node2, delay=delay, bw=self.link_bandwidth)
