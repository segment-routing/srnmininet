
import heapq
import json
import mininet.clean
import os
import sys
from mininet.log import lg

from mako import exceptions as mako_exceptions
from ipmininet.iptopo import Overlay
from ipmininet.router.config import OSPF6, Zebra
from ipmininet.router.config.base import Daemon
from ipmininet.router.config.utils import template_lookup
from ipmininet.utils import realIntfList

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

	@property
	def startup_line(self):
		return '{name} {database} --remote={remotes} --pidfile={pid} --logfile={log}' \
			.format(name=self.NAME,
		            database=self.options.database,
		            remotes=" --remote=".join(self.options.remotes),
		            pid=self._file('pid'),
		            log=self.options.logfile)

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
		""":param database: the database name
		   :param remotes: the list of <protocol>:[<ip>]:<port> specs to use to communicate to the OVSDB server
		   :param schema_tables: the ovsdb table descriptions
		   :param version: the version of the ovsdb table descriptions"""

		defaults.database = "SR_test"
		defaults.remotes = ["tcp:[%s]:6640" % itf.ip6 for itf in self._node.intfList()]
		defaults.schema_tables = self._node.schema_tables if self._node.schema_tables else {}
		defaults.version = "0.0.1"
		super(OVSDB, self).set_defaults(defaults)


class SRNZebra(Zebra):
	"""
	This daemon loads Zebra froma modified Quagga.
	"""
	NAME = 'srnzebra'


class SRNOSPF6(OSPF6):
	"""
	This daemon loads OSPF6 froma modified Quagga.
	It enables communication with OVSDB
	"""
	NAME = 'srnospf6d'
	DEPENDS = (SRNZebra,)

	def build(self):
		cfg = super(SRNOSPF6, self).build()

		cfg.ovsdb_adv = self.options.ovsdb_adv
		cfg.ovsdb_database = self.options.ovsdb_database
		cfg.ovsdb_proto = self.options.ovsdb_proto
		cfg.ovsdb_ip6 = self.options.ovsdb_ip6
		cfg.ovsdb_port = self.options.ovsdb_port

		return cfg

	def set_defaults(self, defaults):
		""":param ovsdb_adv: whether this daemon updates the database whenever the network state changes.
		   :param ovsdb_database: the database name
		   :param ovsdb_proto: the list of <protocol>:[<ip>]:<port> specs to use to communicate to the OVSDB server
		   :param ovsdb_port: the version of the ovsdb table descriptions"""

		defaults.ovsdb_adv = False
		defaults.ovsdb_database = "SR_test"
		defaults.ovsdb_proto = "tcp"
		defaults.ovsdb_ip6 = "::1"
		defaults.ovsdb_port = "6640"
		super(SRNOSPF6, self).set_defaults(defaults)


class Named(Daemon):
	NAME = 'named'
	PRIO = 0

	@property
	def startup_line(self):
		return '{name} -c {cfg} -f -u root' \
			.format(name=self.NAME,
		            cfg=self.cfg_filename)

	@property
	def dry_run(self):
		return '{name} {cfg}' \
			.format(name='named-checkconf',
		            cfg=self.cfg_filename)

	def set_defaults(self, defaults):
		super(Named, self).set_defaults(defaults)

	@property
	def zone_cfg_filename(self):
		"""Return the filename in which this daemon rules should be stored"""
		return self._filepath("test.sr.zone")

	@property
	def zone_template_filename(self):
		return "test.sr.mako"

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

		cfg.ovsdb_client = self.options.ovsdb_client
		cfg.ovsdb_server = "%s:[%s]:%s" %(self.options.ovsdb_server_proto,
		                                  self.options.ovsdb_server_ip,
		                                  self.options.ovsdb_server_port)
		cfg.ovsdb_database = self.options.ovsdb_database
		cfg.ntransacts = self.options.ntransacts

		return cfg

	@property
	def dry_run(self):
		return '{name} -d {cfg}' \
			.format(name=self.NAME,
		            cfg=self.cfg_filename)

	def set_defaults(self, defaults):
		""":param ovsdb_client: the command to run OVSDB client executable
		   :param ovsdb_server_proto: the protocol to communicate to the OVSDB server
		   :param ovsdb_server_ip: the address to communicate to the OVSDB server
		   :param ovsdb_server_port: the port to communicate to the OVSDB server
		   :param ovsdb_database: the name of the database to synchronize
		   :param ntransacts: the number of threads sending transaction RPCs to OVSDB"""

		defaults.ovsdb_client = "ovsdb-client"
		defaults.ovsdb_server_proto = "tcp"
		defaults.ovsdb_server_ip = "::1"
		defaults.ovsdb_server_port = "6640"
		defaults.ovsdb_database = "SR_test"
		defaults.ntransacts = 1
		super(SRNDaemon, self).set_defaults(defaults)


class SRDNSProxy(SRNDaemon):
	NAME = 'sr-dnsproxy'
	DEPENDS = (Named, OVSDB)

	def build(self):
		cfg = super(SRDNSProxy, self).build()

		cfg.router_name = self._node.name
		cfg.max_queries = self.options.max_queries

		cfg.dns_server = "::1"  # Acceptable since "Named" is a required daemon
		cfg.dns_server_port = self.options.dns_server_port

		cfg.proxy_listen_port = self.options.proxy_listen_port

		return cfg

	def set_defaults(self, defaults):
		""":param max_queries: The max number of pending DNS queries
		   :param dns_server_port: Port number of the DNS server
		   :param proxy_listen_port: Listening port of this daemon for external requests"""

		defaults.max_queries = 500
		defaults.dns_server_port = 53
		defaults.proxy_listen_port = 2000

		super(SRDNSProxy, self).set_defaults(defaults)


class SRCtrl(SRNDaemon):
	NAME = 'sr-ctrl'
	DEPENDS = (OVSDB, SRNOSPF6, SRDNSProxy, Named)

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
		cfg.dns_fifo = self._file(".fifo")
		cfg.iproute = "ip -6"
		cfg.vnhpref = "ffff::"
		cfg.ingress_iface = "lo"

		if self._node.sr_controller is None:
			lg.error('No DNS Proxy specified for DNS forwarder, aborting!')
			mininet.clean.cleanup()
			sys.exit(1)
		self.options.ovsdb_server_ip = self.find_closest_intf(self._node, self._node.sr_controller)
		if self.options.ovsdb_server_ip is None:
			lg.error('Cannot find an SR controller in the same AS, aborting!')
			mininet.clean.cleanup()
			sys.exit(1)
		cfg.ovsdb_server = "%s:[%s]:%s" %(self.options.ovsdb_server_proto,
		                                  self.options.ovsdb_server_ip,
		                                  self.options.ovsdb_server_port)

		return cfg

	@staticmethod
	def cost_intf(intf):
		return intf.delay if intf.delay else SRRouted.DEFAULT_COST

	@staticmethod
	def find_closest_intf(base, sr_controller):

		if base.name == sr_controller:
			return "::1"

		visited = set()
		to_visit = [(SRRouted.cost_intf(intf), intf) for intf in realIntfList(base)]
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
					return ip if ip else peer_intf.ip6
				elif peer_intf.node.asn == base.asn or not peer_intf.node.asn:
					for x in realIntfList(peer_intf.node):
						heapq.heappush(to_visit, (cost + SRRouted.cost_intf(x), x))
		return None


class SRDNSFwd(SRNDaemon):
	NAME = 'sr-dnsfwd'
	DEPENDS = (SRRouted,)

	def build(self):
		cfg = super(SRDNSFwd, self).build()

		cfg.router_name = self._node.name
		cfg.max_queries = self.options.max_queries

		# Valid since SRRouted will be started faster
		cfg.dns_fifo = self._node.config.daemon(SRRouted.NAME).options.dns_fifo

		if self._node.sr_controller is None:
			lg.error('No DNS Proxy specified for DNS forwarder, aborting!')
			mininet.clean.cleanup()
			sys.exit(1)
		cfg.dns_proxy = self._node.config.daemon(SRRouted.NAME).options.ovsdb_server_ip
		if cfg.dns_proxy is None:
			lg.error('Cannot find an SR controller in the same AS, aborting!')
			mininet.clean.cleanup()
			sys.exit(1)

		cfg.proxy_listen_port = self.options.proxy_listen_port
		cfg.dnsfwd_listen_port = self.options.dnsfwd_listen_port

		return cfg

	def set_defaults(self, defaults):
		""":param max_queries: The max number of pending DNS queries
		   :param dns_server_port: Port number of the DNS server
		   :param proxy_listen_port: Listening port of this daemon for external requests"""

		defaults.max_queries = 500
		defaults.proxy_listen_port = 2000
		defaults.dnsfwd_listen_port = 2000

		super(SRDNSFwd, self).set_defaults(defaults)
