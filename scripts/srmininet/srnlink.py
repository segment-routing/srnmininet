
import re
from ipaddress import ip_interface
from mininet.log import lg

from ipmininet.link import TCIntf


class SRNTCIntf(TCIntf):

	def __init__(self, *args, **kwargs):
		super(SRNTCIntf, self).__init__(*args, **kwargs)
		self.delay = kwargs.get("delay", 0)
		self.bw = kwargs.get("bw", 0)

	def bwCmds(self, htb_burst=None, **params):
		"""Return tc commands to set bandwidth.
		   This version adds burst (in kB) for the htb qdisc."""
		cmds, parent = super(SRNTCIntf, self).bwCmds(**params)

		found = False
		if htb_burst is not None and htb_burst < 0:
			lg.error("Burst for htb %d is not a positive value" % htb_burst)
			cmds, parent = [], ' root '
		else:
			for idx in range(len(cmds)):
				if "htb" in cmds[idx] and "burst" in cmds[idx]:
					if htb_burst is not None:
						cmds[idx] = re.sub(r"burst \d+k", "burst %dk" % htb_burst, cmds[idx])
					else:
						cmds[idx] = re.sub(r"burst \d+k", "", cmds[idx])
						found = True
					break

		if found:
			# FIXME parent id should not be hardcoded
			cmds.append("%s filter add dev %s protocol ipv6 parent 5: prio 1 u32 match ip6 dst ::/0 flowid 1:1")

		return cmds, parent

	def _del_ip(self, ip):
		if self.name != 'lo' or ip != ip_interface("::1"):
			super(SRNTCIntf, self)._del_ip(ip)
