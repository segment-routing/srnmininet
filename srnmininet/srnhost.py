from ipmininet.host import IPHost
from ipmininet.srv6 import enable_srv6


class SRNHost(IPHost):

    def start(self):
        enable_srv6(self)
        super().start()
