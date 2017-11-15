
import heapq
import json
import os
import time
from copy import deepcopy
from mininet.log import lg

from ipmininet.iptopo import Overlay
from ipmininet.router.config import OSPF6, Zebra
from ipmininet.router.config.base import Daemon
from ipmininet.router.config.utils import ConfigDict, template_lookup
from ipmininet.utils import L3Router, realIntfList
from mako import exceptions as mako_exceptions

template_lookup.directories.append(os.path.join(os.path.dirname(__file__), 'templates'))


class SRCtrlDomain(Overlay):

	def __init__(self, access_routers, sr_controller, schema_tables):  # TODO Add marker for access router

		super(SRCtrlDomain, self).__init__(nodes=access_routers,
		                                   nprops={"sr_controller": sr_controller, "schema_tables": schema_tables})
		if sr_controller not in self.nodes:
			self.add_node(sr_controller)

		for n in access_routers:
			self.set_node_property(n, "access_router", True)
			self.set_node_property(n, "sr_controller", sr_controller)
		self.set_node_property(sr_controller, "schema_tables", schema_tables)


class OVSDB(Daemon):
	NAME = 'ovsdb-server'
	PRIO = 0

	OVSDB_INSERT_FORMAT = "[\"%s\",{\"row\":%s,\"table\":\"%s\",\"op\":\"insert\"}]"

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
		cfg = super(OVSDB, self).build()

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
		                    for itf in self._node.intfList()
		                    for ip6 in itf.ip6s(exclude_lls=True)]
		defaults.schema_tables = self._node.schema_tables if self._node.schema_tables else {}
		defaults.version = "0.0.1"
		super(OVSDB, self).set_defaults(defaults)

	def has_started(self):
		# We override this such that we wait until we have the command socket
		if os.path.exists(self._file('ctl')):
			time.sleep(1)  # FIXME Ugly but no better idea
			return True
		return False

	@staticmethod
	def extract_client_remote(remote):
		remote_split = remote.split(":")
		proto = remote_split[0]
		port = remote_split[-1]
		addr = remote[2+len(proto):len(remote)-len(port)-2]
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
		return self._node.cmd("%s transact %s '%s'" % (self.options.ovsdb_client,
		                                               self._remote_server_to_client().next(),
		                                               insert))


class SRNOSPF6(OSPF6):
	"""
	This daemon loads OSPF6 froma modified Quagga.
	It enables communication with OVSDB
	"""
	DEPENDS = (Zebra,)

	def build(self):
		cfg = super(SRNOSPF6, self).build()

		cfg.ovsdb_adv = self.options.ovsdb_adv
		if cfg.ovsdb_adv:
			sr_controller_ip, ovsdb = find_closest_intf(self._node, self._node.sr_controller)
			cfg.ovsdb_server = ovsdb.remote_server_to_client(sr_controller_ip)
			cfg.ovsdb_database = ovsdb.options.database
			cfg.ovsdb_client = ovsdb.options.ovsdb_client
			cfg.ovsdb_proto, cfg.ovsdb_ip6, cfg.ovsdb_port = ovsdb.extract_client_remote(cfg.ovsdb_server)

		if not self.options.logobj:
			self.options.logobj = open(self.options.logfile + ".stdout", "a+")

		return cfg

	def set_defaults(self, defaults):
		""":param ovsdb_adv: whether this daemon updates the database whenever the network state changes."""
		defaults.ovsdb_adv = False
		super(SRNOSPF6, self).set_defaults(defaults)

	def cleanup(self):
		if self.options.logobj:
			self.options.logobj.close()

		super(SRNOSPF6, self).cleanup()

	@property
	def template_filename(self):
		return 'srn%s.mako' % self.NAME


class Named(Daemon):
	NAME = 'named'
	PRIO = 0
	ARMOR_CFG_FILE = "/etc/apparmor.d/local/usr.sbin.named"

	def __init__(self, node, **kwargs):
		super(Named, self).__init__(node, **kwargs)
		self.armor_old_config = None

	def _allow_apparmor(self):
		"""Config Apparmor to allow named to access the cwd"""
		self.armor_old_config = []
		with open(self.ARMOR_CFG_FILE, "r") as fileobj:
			self.armor_old_config = fileobj.readlines()
		armor_new_config = deepcopy(self.armor_old_config)
		armor_new_config.append("%s/** rw,\n" % os.path.abspath(self._node.cwd))
		armor_new_config.append("%s rw,\n" % os.path.abspath(self._node.cwd))
		with open(self.ARMOR_CFG_FILE, "w") as fileobj:
			fileobj.writelines(armor_new_config)
		self._node.cmd(["/etc/init.d/apparmor", "restart"])

	@property
	def startup_line(self):
		return '{name} -c {cfg} -f -u root -p {port}' \
			.format(name=self.NAME,
		            cfg=self.cfg_filename,
		            port=self.options.dns_server_port)

	@property
	def dry_run(self):
		return '{name} {cfg}' \
			.format(name='named-checkconf', cfg=self.cfg_filename)

	def build(self):
		cfg = super(Named, self).build()
		cfg.abs_logfile = os.path.abspath(cfg.logfile)
		cfg.zone = self.options.zone
		cfg.zone_cfg_filename = os.path.abspath(self.zone_cfg_filename)
		cfg.ns = [ip6.ip.compressed for itf in self._node.intfList() for ip6 in itf.ip6s(exclude_lls=True)]
		cfg.hosts = [ConfigDict(name=host.name, ip6s=[ip6.ip.compressed for itf in realIntfList(host)
		                                              for ip6 in itf.ip6s(exclude_lls=True)])
		             for host in self._find_hosts()]
		# Add exception in apparmor
		self._allow_apparmor()
		return cfg

	def _find_hosts(self):
		"""Return the list of connected hosts in the ASN"""
		base = self._node
		visited = set()
		to_visit = realIntfList(base)
		hosts = []

		while to_visit:
			i = to_visit.pop()
			if i in visited:
				continue
			visited.add(i)
			for n in i.broadcast_domain:
				if L3Router.is_l3router_intf(n):
					if n.node.asn == base.asn or not n.node.asn:
						to_visit.extend(realIntfList(n.node))
				else:
					if n not in hosts:
						hosts.append(n.node)
		return hosts

	def set_defaults(self, defaults):
		""":param dns_server_port: The port number of the dns server
		   :param zone: The local zone of name server"""
		defaults.dns_server_port = 2000
		defaults.zone = "test.sr."
		super(Named, self).set_defaults(defaults)

	def cleanup(self):
		super(Named, self).cleanup()
		if self.armor_old_config is not None:
			with open(self.ARMOR_CFG_FILE, "w") as fileobj:
				fileobj.writelines(self.armor_old_config)
			self._node.cmd(["/etc/init.d/apparmor", "restart"])


	@property
	def zone_cfg_filename(self):
		"""Return the filename in which this daemon rules should be stored"""
		return self._filepath("%szone" % self.options.zone)

	@property
	def zone_template_filename(self):
		return "zone.mako"

	def render(self, cfg, **kwargs):

		cfg_content = [super(Named, self).render(cfg, **kwargs)]

		self.files.append(self.zone_cfg_filename)
		lg.debug('Generating %s\n' % self.zone_cfg_filename)
		try:
			cfg_content.append(template_lookup.get_template(self.zone_template_filename).render(node=cfg, **kwargs))
			return cfg_content
		except:
			# Display template errors in a less cryptic way
			lg.error('Couldn''t render a config file(',
			          self.zone_template_filename, ')')
			lg.error(mako_exceptions.text_error_template().render())
			raise ValueError('Cannot render the DNS zone configuration [%s: %s]' % (
				self._node.name, self.NAME))

	def write(self, cfg):

		super(Named, self).write(cfg[0])
		with open(self.zone_cfg_filename, 'w') as f:
			f.write(cfg[1])


class SRNDaemon(Daemon):

	@property
	def startup_line(self):
		return '{name} {cfg}' \
			   .format(name=self.NAME,
		               cfg=self.cfg_filename)

	def build(self):
		cfg = super(SRNDaemon, self).build()

		sr_controller_ip, ovsdb = find_closest_intf(self._node, self._node.sr_controller)
		self.options.sr_controller_ip = sr_controller_ip
		cfg.ovsdb_server = ovsdb.remote_server_to_client(sr_controller_ip)
		cfg.ovsdb_database = ovsdb.options.database
		cfg.ovsdb_client = ovsdb.options.ovsdb_client
		cfg.ntransacts = self.options.ntransacts

		if not self.options.logobj:
			self.options.logobj = open(self.options.logfile, "a+")

		return cfg

	@property
	def dry_run(self):
		return '{name} -d {cfg}' \
			.format(name=self.NAME,
		            cfg=self.cfg_filename)

	def set_defaults(self, defaults):
		""":param ntransacts: the number of threads sending transaction RPCs to OVSDB"""
		defaults.ntransacts = 1
		super(SRNDaemon, self).set_defaults(defaults)

	def cleanup(self):
		if self.options.logobj:
			self.options.logobj.close()

		super(SRNDaemon, self).cleanup()


class SRDNSProxy(SRNDaemon):
	NAME = 'sr-dnsproxy'
	DEPENDS = (Named, OVSDB)

	def build(self):
		cfg = super(SRDNSProxy, self).build()

		cfg.router_name = self._node.name
		cfg.max_queries = self.options.max_queries

		cfg.dns_server = self.options.sr_controller_ip  # Acceptable since "Named" is a required daemon with OVSDB
		cfg.dns_server_port = self._node.config.daemon(Named.NAME).options.dns_server_port

		cfg.proxy_listen_addr = self.options.sr_controller_ip  # Acceptable since we require the daemon with OVSDB
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

		super(SRDNSProxy, self).set_defaults(defaults)


class SRCtrl(SRNDaemon):
	NAME = 'sr-ctrl'
	DEPENDS = (OVSDB, SRDNSProxy, Named)

	def build(self):
		cfg = super(SRCtrl, self).build()

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

		super(SRCtrl, self).set_defaults(defaults)

	@property
	def rules_cfg_filename(self):
		"""Return the filename in which this daemon rules should be stored"""
		return self._filepath("%s-rules.cfg" % self.NAME)

	@property
	def rules_template_filename(self):
		return "%s-rules.mako" % self.NAME

	def render(self, cfg, **kwargs):

		cfg_content = [super(SRCtrl, self).render(cfg, **kwargs)]

		self.files.append(self.rules_cfg_filename)
		lg.debug('Generating %s\n' % self.rules_cfg_filename)
		try:
			cfg_content.append(template_lookup.get_template(self.rules_template_filename).render(node=cfg, **kwargs))
			return cfg_content
		except:
			# Display template errors in a less cryptic way
			lg.error('Couldn''t render a config file(',
			          self.rules_template_filename, ')')
			lg.error(mako_exceptions.text_error_template().render())
			raise ValueError('Cannot render the rules configuration [%s: %s]' % (
				self._node.name, self.NAME))

	def write(self, cfg):

		super(SRCtrl, self).write(cfg[0])
		with open(self.rules_cfg_filename, 'w') as f:
			f.write(cfg[1])


class SRRouted(SRNDaemon):
	NAME = 'sr-routed'
	PRIO = 1  # If OVSDB is on the same router
	DEFAULT_COST = 0.000001

	def build(self):
		cfg = super(SRRouted, self).build()
		cfg.router_name = self._node.name
		cfg.iproute = "ip -6"
		cfg.vnhpref = "ffff::"
		cfg.ingress_iface = "lo"
		return cfg


def ovsdb_daemon(node):
	return node.config.daemon(OVSDB.NAME)


def cost_intf(intf):
	return intf.delay if intf.delay else SRRouted.DEFAULT_COST


def find_closest_intf(base, sr_controller):

	if base.name == sr_controller:
		return (base.intf("lo").ip6 or "::1"), ovsdb_daemon(base)

	visited = set()
	to_visit = [(cost_intf(intf), intf) for intf in realIntfList(base)]
	heapq.heapify(to_visit)

	# Explore all interfaces in base ASN recursively, until we find one
	# connected to the SRN controller.
	while to_visit:
		cost, intf = heapq.heappop(to_visit)
		if intf in visited:
			continue
		visited.add(intf)
		for peer_intf in intf.broadcast_domain.routers:
			if peer_intf.node.name == sr_controller:
				ip = peer_intf.ip
				return (ip if ip else peer_intf.ip6), ovsdb_daemon(peer_intf.node)
			elif peer_intf.node.asn == base.asn or not peer_intf.node.asn:
				for x in realIntfList(peer_intf.node):
					heapq.heappush(to_visit, (cost + cost_intf(x), x))
	return None
