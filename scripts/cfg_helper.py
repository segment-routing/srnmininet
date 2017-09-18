import argparse
import json
import os
import signal
from mininet.log import LEVELS, lg

import ipmininet

from srmininet.square_axa import SquareAxA
from srmininet.srnnet import SRNNet

topo_classes = [SquareAxA]
TOPOS = {topo.__name__:topo for topo in topo_classes}

components = ["sr-ctrl", "sr-routed", "sr-dnsproxy", "sr-dnsfwd", "sr-nsd"]

# Argument parsing

def parse_args():
	parser = argparse.ArgumentParser()
	parser.add_argument('--topo', choices=TOPOS.keys(),
						default=TOPOS.keys()[0],
						help='The topology that you want to start.')
	parser.add_argument('--log', choices=LEVELS.keys(), default='info',
						help='The level of details in the logs.')
	parser.add_argument('--topo-args', help='Additional arguments to give'
	                                        'to the topology constructor (key=val, key=val, ...)',
	                    default='')
	parser.add_argument('--net-args', help='Additional arguments to give'
	                                       'to the network constructor (key=val, key=val, ...)',
	                    default='')
	parser.add_argument('--log-dir', help='Logging directory root',
	                    default='')
	parser.add_argument('--src-dir', help='Source directory root of SR components',
	                    default='')
	parser.add_argument('--pid', help='Path to the file that will contain the pid of this process',
	                    default='')
	return parser.parse_args()


def parse_key_value_args(args):
	dict_args = {}
	for arg in args.strip(' \r\t\n').split(','):
		arg = arg.strip(' \r\t\n')
		if not arg:
			continue
		try:
			k, v = arg.split('=')
			dict_args[k] = v
		except ValueError:
			lg.error('Ignoring args:', arg)
	return dict_args


args = parse_args()

lg.setLogLevel(args.log)
if args.log == 'debug':
	ipmininet.DEBUG_FLAG = True

topo_args = parse_key_value_args(args.topo_args)
topo_args["cwd"] = args.log_dir
net_args = parse_key_value_args(args.net_args)

# Add SR components to PATH

pathlist = [os.path.join(os.path.abspath(args.src_dir), comp) for comp in components]
os.environ["PATH"] += os.pathsep + os.pathsep.join(pathlist)

# Give the database description to the topology

with open(os.path.join(args.src_dir, "sr.ovsschema"), "r") as fileobj:
	full_schema = json.load(fileobj)
	print(str(full_schema))
	topo_args["schema_tables"] = full_schema["tables"]

# Start network and add pid file

net = SRNNet(topo=TOPOS[args.topo](**topo_args), **net_args)

pidfile = args.pid
with open(pidfile, "w") as fileobj:
	fileobj.write(str(os.getpid()))


def handler(signum, frame):
	net.stop()
	os.unlink(pidfile)


net.start()

signal.signal(signal.SIGINT, handler)
