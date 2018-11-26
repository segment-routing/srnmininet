import os

from ipmininet.iptopo import IPTopo


class SRNTopo(IPTopo):

    def __init__(self, controllers, cwd=None, *args, **kwargs):
        """:param controllers: The name (or list of names) of routers that will run a SRN controller"""

        self.access_routers = []
        self.cwd = cwd
        self.controllers = [controllers] if isinstance(controllers, str) else list(controllers)

        super(SRNTopo, self).__init__(*args, **kwargs)

    def addRouter(self, name, controller=False, **params):
        if self.cwd is not None and "cwd" not in params:
            params["cwd"] = os.path.join(self.cwd, name)
        return super(SRNTopo, self).addRouter(name, controller=controller, **params)
