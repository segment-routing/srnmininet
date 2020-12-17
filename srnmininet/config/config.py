import heapq
import json
import os
import re
import time

from ipmininet.host import IPHost
from ipmininet.host.config import Named, DNSZone
from ipmininet.iptopo import Overlay
from ipmininet.router.config import OSPF6, Zebra
from ipmininet.router.config.base import Daemon, RouterDaemon
from ipmininet.utils import realIntfList
from mako.lookup import TemplateLookup
from mininet.log import lg

from srnmininet.srntopo import SRNTopo

__TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), 'templates')
srn_template_lookup = TemplateLookup(directories=[__TEMPLATES_DIR])


class SRCtrlDomain(Overlay):

    def __init__(self, access_routers, sr_controller, schema_tables, hosts=()):  # TODO Add marker for access router

        super().__init__(nodes=access_routers, nprops={"sr_controller": sr_controller, "schema_tables": schema_tables})
        self.zone = DNSZone(name="test.sr", dns_master=sr_controller, nodes=self.nodes + list(hosts))
        if sr_controller not in self.nodes:
            self.add_node(sr_controller)

        for n in access_routers:
            self.set_node_property(n, "access_router", True)
            self.set_node_property(n, "sr_controller", sr_controller)
        self.set_node_property(sr_controller, "schema_tables", schema_tables)
        self.set_node_property(sr_controller, "controller", True)

    def check_consistency(self, topo: 'SRNTopo') -> bool:
        return super().check_consistency(topo) and self.zone.check_consistency(topo)

    def apply(self, topo: 'SRNTopo'):
        self.zone.apply(topo)
        super().apply(topo)


class OVSDB(RouterDaemon):
    NAME = 'ovsdb-server'
    KILL_PATTERNS = (NAME,)
    PRIO = 0

    OVSDB_INSERT_FORMAT = "[\"%s\",{\"row\":%s,\"table\":\"%s\",\"op\":\"insert\"}]"

    def __init__(self, node, template_lookup=srn_template_lookup, **kwargs):
        super().__init__(node, template_lookup=template_lookup,
                         **kwargs)

    @property
    def startup_line(self):
        return '{name} {database} --remote={remotes} --pidfile={pid} --log-file={log} --unixctl={ctl}' \
            .format(name=self.NAME,
                    database=os.path.join(self._node.cwd, self.options.database),
                    remotes=" --remote=".join(self.options.remotes),
                    pid=os.path.abspath(self._file('pid')),
                    log=self.options.logfile,
                    ctl=os.path.abspath(self._file('ctl')))

    def build(self):
        cfg = super().build()

        cfg.version = self.options.version
        cfg.database = self.options.database
        cfg.schema_tables = json.dumps(self.options.schema_tables, indent=4)

        return cfg

    @property
    def dry_run(self):
        """Creates the database file from the schema"""
        return '{name} create {database} {schema}' \
            .format(name='ovsdb-tool',
                    log=self.options.logfile,
                    database=os.path.join(self._node.cwd, self.options.database),
                    schema=self.cfg_filename)

    def set_defaults(self, defaults):
        """:param ovsdb_client: the command to run OVSDB client executable
           :param database: the database name
           :param remotes: the list of <protocol>:<port>:[<ip>] specs to use to communicate to the OVSDB server
           :param schema_tables: the ovsdb table descriptions
           :param version: the version of the ovsdb table descriptions"""
        defaults.ovsdb_client = "ovsdb-client"
        defaults.database = "SR_test"
        defaults.remotes = ["ptcp:6640:[%s]" % ip6.ip.compressed
                            for itf in realIntfList(self._node) + [self._node.intf('lo')]
                            for ip6 in itf.ip6s(exclude_lls=True, exclude_lbs=False)]
        defaults.schema_tables = self._node.schema_tables if self._node.schema_tables else {}
        defaults.version = "0.0.1"
        super().set_defaults(defaults)

    def has_started(self):
        # We override this such that we wait until we have the command socket
        if os.path.exists(self._file('ctl')):
            cmds = [["ovsdb-client", "get-schema", remote, self.options.database]
                    for remote in self._remote_server_to_client()]
            i = 0
            while True:
                i += 1
                try:
                    for cmd in cmds:
                        self._node.cmd(cmd)
                    time.sleep(1)
                    break
                except Exception:
                    if i > 90:
                        raise Exception("Cannot connect to OVSDB server")
            return True
        return False

    @staticmethod
    def extract_client_remote(remote):
        remote_split = remote.split(":")
        proto = remote_split[0]
        port = remote_split[-1]
        addr = remote[2 + len(proto):len(remote) - len(port) - 2]
        return proto, addr, port

    def _remote_server_to_client(self):
        """The remote parameter of the client-side ovsdb is different by the order <protocol>:[<ip>]:<port>
           and by the protocols available (no protocol name starting by 'p')"""

        for server_remote in self.options.remotes:
            proto = server_remote.split(":")[0]

            # Only "listener protocol names"
            if proto[0] != "p":
                continue

            proto = proto[1:]
            port = server_remote.split(":")[1]
            addr = server_remote[3 + len(proto) + len(port):]
            yield "%s:%s:%s" % (proto, addr, port)

    def remote_server_to_client(self, remote_ip):
        for remote in self._remote_server_to_client():
            if "[%s]" % remote_ip in remote:
                return remote
        return None

    def insert_entry(self, table_name, content):
        insert = self.OVSDB_INSERT_FORMAT % (self.options.database, json.dumps(content), table_name)
        cmd = "%s transact %s '%s'" % (self.options.ovsdb_client, next(self._remote_server_to_client()), insert)
        print(cmd)  # TODO Remove
        return self._node.cmd(cmd)


class SRNOSPF6(OSPF6):
    """
    This daemon loads OSPF6 froma modified Quagga.
    It enables communication with OVSDB
    """
    DEPENDS = (Zebra,)

    def __init__(self, node, template_lookup=srn_template_lookup, **kwargs):
        super().__init__(node, template_lookup=template_lookup,
                         **kwargs)

    def build(self):
        cfg = super().build()

        cfg.ovsdb_adv = self.options.ovsdb_adv
        if cfg.ovsdb_adv:
            sr_controller_ip, ovsdb = find_controller(self._node, self._node.sr_controller)
            cfg.ovsdb_server = ovsdb.remote_server_to_client(sr_controller_ip)
            cfg.ovsdb_database = ovsdb.options.database
            cfg.ovsdb_client = ovsdb.options.ovsdb_client
            cfg.ovsdb_proto, cfg.ovsdb_ip6, cfg.ovsdb_port = ovsdb.extract_client_remote(cfg.ovsdb_server)

        return cfg

    def set_defaults(self, defaults):
        """:param ovsdb_adv: whether this daemon updates the database whenever the network state changes."""
        defaults.ovsdb_adv = False
        super().set_defaults(defaults)

    @property
    def template_filename(self):
        return 'srn%s.mako' % self.NAME


# Do not get a router id => can be run on hosts as well
class ZlogDaemon(Daemon):
    """
    Class for daemons using zlog
    """
    DEBUG = "debug"
    INFO = "info"
    NOTICE = "notice"
    WARN = "warn"
    ERROR = "error"
    FATAL = "fatal"

    def __init__(self, node, template_lookup=srn_template_lookup, **kwargs):
        super().__init__(node,
                         template_lookup=template_lookup,
                         **kwargs)

    def build(self):
        cfg = super().build()
        cfg.zlog_cfg_filename = self.zlog_cfg_filename
        cfg.loglevel = self.options.loglevel
        return cfg

    def set_defaults(self, defaults):
        """:param loglevel: the minimum loglevel that is written in logfile"""
        defaults.loglevel = self.DEBUG
        super().set_defaults(defaults)

    @property
    def zlog_cfg_filename(self):
        """Return the filename in which this daemon log rules should be stored"""
        return self._filepath("%s-zlog.cfg" % self.NAME)

    @property
    def zlog_template_filename(self):
        return "zlog.mako"

    @property
    def cfg_filenames(self):
        return super().cfg_filenames + \
               [self.zlog_cfg_filename]

    @property
    def template_filenames(self):
        return super().template_filenames + \
               [self.zlog_template_filename]

    def render(self, cfg, **kwargs):
        # So that it works for all daemons extending this class
        cfg["zlog"] = cfg[self.NAME]
        return super().render(cfg, **kwargs)


class SRNDaemon(ZlogDaemon):

    @property
    def startup_line(self):
        return '{name} {cfg}' \
            .format(name=self.NAME,
                    cfg=self.cfg_filename)

    def build(self):
        cfg = super().build()

        sr_controller_ip, ovsdb = find_controller(self._node, self._node.sr_controller)
        self.options.sr_controller_ip = sr_controller_ip
        cfg.ovsdb_server = ovsdb.remote_server_to_client(sr_controller_ip)
        cfg.ovsdb_database = ovsdb.options.database
        cfg.ovsdb_client = ovsdb.options.ovsdb_client
        cfg.ntransacts = self.options.ntransacts
        cfg.extras = self.options.extras

        return cfg

    @property
    def dry_run(self):
        return '{name} -d {cfg}' \
            .format(name=self.NAME,
                    cfg=self.cfg_filename)

    def set_defaults(self, defaults):
        """:param ntransacts: the number of threads sending transaction RPCs to OVSDB
           :param extras: a dict of {"key": value} with parameters to be inserted as is in the template
           (value type must be either int or string)"""
        defaults.ntransacts = 1
        defaults.extras = {}
        super().set_defaults(defaults)


class SRNNamed(Named):

    def set_defaults(self, defaults):
        super().set_defaults(defaults)
        defaults.dns_server_port = 2000


class SRDNSProxy(SRNDaemon):
    NAME = 'sr-dnsproxy'
    DEPENDS = (SRNNamed, OVSDB)
    KILL_PATTERNS = (NAME,)

    def build(self):
        cfg = super().build()

        cfg.router_name = self._node.name
        cfg.max_queries = self.options.max_queries

        cfg.dns_server = self.options.sr_controller_ip  # Acceptable since "Named" is a required daemon with OVSDB
        cfg.dns_server_port = self._node.nconfig.daemon(
            SRNNamed.NAME).options.dns_server_port

        # XXX Does not work if we listen on all addresses because it might reply with another address
        # than the one sue to reach it
        cfg.proxy_listen_addr = self._node.intf("lo").ip6
        cfg.proxy_listen_port = self.options.proxy_listen_port

        cfg.client_server_fifo = self.options.client_server_fifo
        self.files.append(cfg.client_server_fifo)

        return cfg

    def set_defaults(self, defaults):
        """:param max_queries: The max number of pending DNS queries
           :param proxy_listen_port: Listening port of this daemon for external requests
           :param client_server_fifo: The file path for the creation of a fifo (for interal usage)"""

        defaults.max_queries = 500
        defaults.proxy_listen_port = 53
        defaults.client_server_fifo = os.path.join("/tmp", self._filename(suffix='fifo'))

        super().set_defaults(defaults)


class SRCtrl(SRNDaemon):
    NAME = 'sr-ctrl'
    DEPENDS = (OVSDB, SRDNSProxy, SRNNamed)
    KILL_PATTERNS = (NAME,)

    def build(self):
        cfg = super().build()

        cfg.rules_file = self.rules_cfg_filename
        cfg.worker_threads = self.options.worker_threads
        cfg.req_buffer_size = self.options.req_buffer_size

        return cfg

    def set_defaults(self, defaults):
        """:param worker_threads: The number of workers handling requests
           :param req_buffer_size: The size of the request buffer
           :param providers: The list of providers with their supplied PA"""

        defaults.worker_threads = 1
        defaults.req_buffer_size = 16

        super().set_defaults(defaults)

    @property
    def rules_cfg_filename(self):
        """Return the filename in which this daemon rules should be stored"""
        return self._filepath("%s-rules.cfg" % self.NAME)

    @property
    def rules_template_filename(self):
        return "%s-rules.mako" % self.NAME

    @property
    def cfg_filenames(self):
        return super().cfg_filenames + \
               [self.rules_cfg_filename]

    @property
    def template_filenames(self):
        return super().template_filenames + \
               [self.rules_template_filename]


class SRRouted(SRNDaemon):
    NAME = 'sr-routed'
    PRIO = 1  # If OVSDB is on the same router
    DEFAULT_COST = 0.000001

    def __init__(self, node, **kwargs):
        super().__init__(node, **kwargs)
        self.localsid_idx = -1
        self.localsid_name = None

    def build(self):
        cfg = super().build()
        cfg.router_name = self._node.name
        cfg.ingress_iface = realIntfList(self._node)[0]
        cfg.localsid = self.add_localsid_table()
        return cfg

    def rt_tables_line(self):
        return "%d\t%s\n" % (self.localsid_idx, self.localsid_name)

    def add_localsid_table(self):

        # Create name and index of the node local SID table

        reg = re.compile("([0-9]+)\t+(.+)")
        reserved_ids = []
        reserved_names = []
        with open("/etc/iproute2/rt_tables") as fileobj:
            for line in fileobj:
                if len(line) == 0 or line[0] == "#":
                    continue
                match = reg.search(line)
                if match is not None:
                    reserved_ids.append(int(match.group(1)))
                    reserved_names.append(str(match.group(2)))

        localsid_name = "%s.%s" % (self._node.name, "localsid")
        i = 0
        while localsid_name in reserved_names:
            localsid_name = "%s.%s.%d" % (self._node.name, "localsid", i)
            i += 1
        self.localsid_name = localsid_name

        i = 1
        while i < 2 ** 32:
            if i not in reserved_ids:
                self.localsid_idx = i
                break
            i += 1

        if self.localsid_idx > 0:
            with open("/etc/iproute2/rt_tables", "a+") as fileobj:
                fileobj.write(self.rt_tables_line())

            # Add a rule so that traffic directed to loopback prefix is transferred to the localsid table

            for ip6 in self._node.intf("lo").ip6s(exclude_lls=True, exclude_lbs=True):
                cmd = ["ip", "-6", "rule", "add", "to", ip6.network.with_prefixlen, "lookup", self.localsid_name]
                self._node.cmd(cmd)

        return self.localsid_idx

    def cleanup(self):

        if self.localsid_idx > 0:
            # Flush all the table routes
            cmd = ["ip", "-6", "route", "flush", "table", self.localsid_name]
            try:
                self._node.cmd(cmd)
            except Exception:
                lg.debug("Cannot flush routing table %s", self.localsid_name)

            # Remove the rules pointing to the table
            for ip6 in self._node.intf("lo").ip6s(exclude_lls=True, exclude_lbs=True):
                cmd = ["ip", "-6", "rule", "del", "to", ip6.network.with_prefixlen, "lookup", self.localsid_name]
                try:
                    self._node.cmd(cmd)
                except Exception:
                    pass

            # Clean the entry in the config file
            with open("/etc/iproute2/rt_tables") as fileobj:
                content = fileobj.readlines()
            with open("/etc/iproute2/rt_tables", "w") as fileobj:
                for line in filter(lambda x: self.rt_tables_line() != x, content):
                    fileobj.write(line)

        super().cleanup()


def ovsdb_daemon(node):
    return node.nconfig.daemon(OVSDB.NAME)


def find_controller(base, sr_controller):
    if base.name == sr_controller:
        return (base.intf("lo").ip6 or u"::1"), ovsdb_daemon(base)

    if isinstance(base, IPHost):
        # Get the ASN from the access router
        asn = base.defaultIntf().broadcast_domain.routers[0].node.asn
    else:
        asn = base.asn

    visited = set()
    to_visit = [(0, intf) for intf in realIntfList(base)]
    heapq.heapify(to_visit)

    # Explore all interfaces in base ASN recursively, until we find one
    # connected to the SRN controller.
    while to_visit:
        cost, intf = heapq.heappop(to_visit)
        if intf in visited:
            continue
        visited.add(intf)
        for peer_intf in intf.broadcast_domain.routers:
            if peer_intf == intf:
                continue
            if peer_intf.node.name == sr_controller:
                ip6s = peer_intf.node.intf("lo").ip6s(exclude_lls=True, exclude_lbs=True)
                for ip6 in ip6s:
                    return ip6.ip, ovsdb_daemon(peer_intf.node)
                return peer_intf.ip6, ovsdb_daemon(peer_intf.node)
            elif peer_intf.node.asn == asn or not peer_intf.node.asn:
                for x in realIntfList(peer_intf.node):
                    heapq.heappush(to_visit, (cost + 1, x))
    return None, None
