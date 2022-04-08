from .config import SRCtrlDomain
from .srntopo import SRNTopo


class CompTopo(SRNTopo):
    """
                                +-------+
                        +-------+ comp1 +-------+
                        |       +-------+       |
        +-------+   +---+---+               +---+---+   +-------+
        | comp2 +---+ comp4 |               | comp5 +---+ comp6 |
        +-------+   +---+---+               +---+---+   +-------+
                        |       +-------+       |
                        +-------+ comp3 +-------+
                                +-------+

    The client is on comp2, the server on comp6 and the controller on comp1.
    """

    def __init__(self, schema_tables=None, link_bandwidth=0, link_delay="1ms", *args, **kwargs):
        """:param schema_tables: The schema table of ovsdb
           :param link_bandwidth: The link bandwidth"""
        self.link_delay = link_delay
        self.link_bandwidth = link_bandwidth
        self.schema_tables = schema_tables if schema_tables else {}

        super().__init__("comp1", *args, **kwargs)

    def build(self, *args, **kwargs):
        # Controllers
        controller = self.addRouter(self.controllers[0])

        # Routers
        comp4 = self.addRouter("comp4", lo_addresses=["2042:bac:4::1/64"])
        comp1 = self.addRouter("comp1", lo_addresses=["2042:bac:1::1/64"])
        comp3 = self.addRouter("comp2", lo_addresses=["2042:bac:2::1/64"])
        comp5 = self.addRouter("comp5", lo_addresses=["2042:bac:5::1/64"])

        # Hosts
        comp2 = self.addHost("comp2")
        comp6 = self.addHost("comp6")

        # Links
        self.addLink(comp2, comp4, params1={"ip": ["2042:3:0::2/64"]}, params2={"ip": ["2042:3:0::1/64"]})
        self.addLink(comp4, comp1, params1={"ip": ["2042:0:1::1/64"]}, params2={"ip": ["2042:0:1::2/64"]})
        self.addLink(comp4, comp3, params1={"ip": ["2042:0:2::1/64"]}, params2={"ip": ["2042:0:2::2/64"]})
        self.addLink(comp1, comp5, params1={"ip": ["2042:1:1::2/64"]}, params2={"ip": ["2042:1:1::1/64"]})
        self.addLink(comp3, comp5, params1={"ip": ["2042:1:2::2/64"]}, params2={"ip": ["2042:1:2::1/64"]})
        self.addLink(comp5, comp6, params1={"ip": ["2042:2:1::2/64"]}, params2={"ip": ["2042:2:1::1/64"]})

        # SRN overlay
        self.addOverlay(SRCtrlDomain(access_routers=(comp4, comp5), sr_controller=controller,
                                     schema_tables=self.schema_tables, hosts=self.hosts()))

        super().build(*args, **kwargs)

    def addLink(self, node1, node2, delay=None, **opts):
        delay = self.link_delay if delay is None else delay
        return super().addLink(node1, node2, delay=delay, bw=self.link_bandwidth, **opts)
