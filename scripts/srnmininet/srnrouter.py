
import errno
import mininet.clean
import os
import sys
import time
from mininet.log import lg

from ipmininet.router.config.ospf6 import OSPF6RedistributedRoute
from sr6mininet.sr6router import SR6Config, SR6Router


class SRNConfig(SR6Config):

	def __init__(self, node, additional_daemons=(), *args, **kwargs):
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
		super(SR6Config, self).__init__(node, daemons=d,
		                                *args, **kwargs)


def mkdir_p(path):
	try:
		os.makedirs(path, mode=0777)
	except OSError as exc:
		if exc.errno == errno.EEXIST and os.path.isdir(path):
			pass
		else:
			raise


class SRNRouter(SR6Router):

	def __init__(self, name, config=SRNConfig, cwd="/tmp", static_routing=False, *args, **kwargs):
		super(SRNRouter, self).__init__(name, config=config, cwd=cwd, static_routing=static_routing, *args, **kwargs)
		mkdir_p(cwd)

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

	def start(self):
		"""Start the router: Configure the daemons, set the relevant sysctls,
		and fire up all needed processes"""
		# Build the config
		self.config.build()
		# Check them
		err_code = False
		for d in self.config.daemons:
			out, err, code = self._processes.pexec(*d.dry_run.split(' '))
			err_code = err_code or code
			if code:
				lg.error(d.NAME, 'configuration check failed [rcode:', str(code),
				         ']\nstdout:', str(out), '\nstderr:', str(err))
		if err_code:
			lg.error('Config checks failed, aborting!')
			mininet.clean.cleanup()
			sys.exit(1)
		# Set relevant sysctls
		for opt, val in self.config.sysctl:
			self._old_sysctl[opt] = self._set_sysctl(opt, val)
		# Fire up all daemons
		for d in self.config.daemons:
			kwargs = {"stdout": d.options.logobj, "stderr": d.options.logobj} if d.options.logobj else {}
			self._processes.popen(*d.startup_line.split(' '), **kwargs)
			# Busy-wait if the daemon needs some time before being started
			while not d.has_started():
				time.sleep(.001)

		# Install SRv6 Routes
		if self.srv6_routes is not None:
			for route in self.srv6_routes:
				code = route.install()
				if code:
					lg.error('SRv6 install failed, aborting!')
					mininet.clean.cleanup()
					sys.exit(1)
