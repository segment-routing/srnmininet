import os

from ipmininet.iptopo import IPTopo

MAX_QUEUE = 1000000000


class SRNTopo(IPTopo):

    def __init__(self, controllers, cwd=None, *args, **kwargs):
        """:param controllers: The name (or list of names) of routers that will run a SRN controller"""

        self.access_routers = []
        self.cwd = cwd
        self.controllers = [controllers] if isinstance(controllers, str) else list(controllers)
        self.inter_switches = {}
        self.switch_count = 0

        super().__init__(*args, **kwargs)

    def addRouter(self, name, **params):
        if self.cwd is not None and "cwd" not in params:
            params["cwd"] = os.path.join(self.cwd, name)
        return super().addRouter(name, **params)

    def addLink(self, node1, node2, delay=None, bw=None, max_queue_size=MAX_QUEUE, **opts):
        src_delay = None
        dst_delay = None
        opts1 = dict(opts)
        if "params2" in opts1:
            opts1.pop("params2")
        try:
            src_delay = opts.get("params1", {}).pop("delay")
        except KeyError:
            pass
        opts2 = dict(opts)
        if "params1" in opts2:
            opts2.pop("params1")
        try:
            dst_delay = opts.get("params2", {}).pop("delay")
        except KeyError:
            pass

        src_delay = src_delay if src_delay else delay
        dst_delay = dst_delay if dst_delay else delay

        # Insert intermediate switch
        if src_delay or dst_delay:
            # node1 -> switch
            default_params1 = {"bw": bw}
            default_params1.update(opts.get("params1", {}))
            opts1["params1"] = default_params1

            # node2 -> switch
            default_params2 = {"bw": bw}
            default_params2.update(opts.get("params2", {}))
            opts2["params2"] = default_params2

            # switch -> node1
            opts1["params2"] = {"delay": dst_delay,
                                "max_queue_size": max_queue_size}
            # switch -> node2
            opts2["params1"] = {"delay": src_delay,
                                "max_queue_size": max_queue_size}

            # Netem queues will mess with shaping
            # Therefore, we put them on an intermediary switch
            self.switch_count += 1
            s = "s%d" % self.switch_count
            self.addSwitch(s)
            self.inter_switches.setdefault(node1, {})[node2] = s
            self.inter_switches.setdefault(node2, {})[node1] = s
            return super().addLink(node1, s, **opts1), super().addLink(s, node2, **opts2)

        return super().addLink(node1, node2, **opts)
