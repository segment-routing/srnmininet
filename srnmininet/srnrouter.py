import errno
import os

from ipmininet.router import Router
from ipmininet.router.config import RouterConfig
from ipmininet.router.config.ospf6 import OSPF6RedistributedRoute
from ipmininet.srv6 import enable_srv6
from mininet.log import lg


class SRNConfig(RouterConfig):

    def __init__(self, node: 'SRNRouter', additional_daemons=(), *args, **kwargs):
        """A simple router made of at least an OSPF daemon

        :param additional_daemons: Other daemons that should be used"""
        # Importing here to avoid circular import
        from ipmininet.router.config.ospf import OSPF
        from .config import SRNOSPF6, SRCtrl, SRRouted
        # We don't want any zebra-specific settings, so we rely on the OSPF/OSPF6
        # DEPENDS list for that daemon to run it with default settings
        # We also don't want specific settings beside the defaults, so we don't
        # provide an instance but the class instead
        d = []
        if node.use_v4 and not node.static_routing:
            d.append(OSPF)
        if node.use_v6:
            if node.controller:
                if not node.static_routing:
                    d.append((SRNOSPF6, {'ovsdb_adv': True,
                                         'redistribute': [OSPF6RedistributedRoute("connected")]}))
                d.append(SRCtrl)
            elif not node.static_routing:
                d.append((SRNOSPF6, {'redistribute': [OSPF6RedistributedRoute("connected")]}))
            if node.access_router:
                d.append(SRRouted)
        d.extend(additional_daemons)
        super().__init__(node, daemons=d, *args, **kwargs)


def mkdir_p(path):
    try:
        os.makedirs(path, mode=0o777)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


class SRNRouter(Router):

    def __init__(self, name, config=SRNConfig, cwd="/tmp", static_routing=False, *args, **kwargs):
        # Variables defined before to be accessible for config daemons
        self.static_routing = static_routing
        super().__init__(name, config=config, cwd=cwd, *args, **kwargs)
        mkdir_p(cwd)

    def start(self):
        enable_srv6(self)

        # Set SRv6 source address for encapsulation
        for ip6 in self.intf('lo').ip6s(exclude_lls=True, exclude_lbs=True):
            cmd = ["ip", "sr", "tunsrc", "set", ip6.ip.compressed]
            out, err, code = self.pexec(cmd)
            if code:
                lg.error(self.name, 'Cannot set SRv6 source address [rcode:', str(code),
                         ']\nstdout:', str(out), '\nstderr:', str(err))
            break

        super().start()

    @property
    def controller(self):
        return self.get('controller', False)

    @property
    def access_router(self):
        return self.get('access_router', False)

    @property
    def sr_controller(self):
        return self.get('sr_controller', None)

    @property
    def schema_tables(self):
        return self.get('schema_tables', None)
