from ipmininet.link import IPIntf


class SRNIntf(IPIntf):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.delay = kwargs.get("delay", "0ms")
        self.bw = kwargs.get("bw", 0)

    def config(self, *args, **kwargs):
        r = super().config(*args, **kwargs)
        self.cmd("sysctl net.ipv4.conf.all.rp_filter=0")
        self.cmd("sysctl net.ipv4.conf.default.rp_filter=0")
        self.cmd("sysctl net.ipv4.conf.lo.rp_filter=0")
        self.cmd("sysctl net.ipv4.conf.{}.rp_filter=0".format(self.name))

    def __lt__(self, other):
        return self.name < other.name

    def __eq__(self, other):
        return self.name == other.name

    def __hash__(self):
        return hash(self.name)
