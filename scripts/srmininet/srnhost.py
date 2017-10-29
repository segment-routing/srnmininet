
from mininet.node import Host

from ipmininet.utils import realIntfList


class SRNHost(Host):

	def _set_sysctl(self, key, val):
		"""Change a sysctl value, and return the previous set value"""
		val = str(val)
		try:
			v = self.cmd('sysctl', key) \
				.split('=')[1] \
				.strip(' \n\t\r')
		except IndexError:
			v = None
		if v != val:
			self.cmd('sysctl', '-w', '%s=%s' % (key, val))
		return v

	def enable_srv6(self):
		"""
		Enables SRv6 on all interfaces
		"""
		self._set_sysctl("net.ipv6.conf.all.seg6_enabled", "1")
		for intf in realIntfList(self):
			self._set_sysctl("net.ipv6.conf.%s.seg6_enabled" % intf.name, "1")
