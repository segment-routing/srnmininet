# SRNMininet

This repository includes a library based on [IPMininet](https://github.com/cnp3/ipmininet)
and scripts to quickly emulate
a [Software Resolved Network \(SRN)](https://github.com/segment-routing/srn).

## Getting started

You first need to install IPMininet and its daemons separately.
The procedure is detailed in their
[installation guide](https://ipmininet.readthedocs.io/en/latest/install.html).

You then need to clone and compile [SRN](https://github.com/segment-routing/srn).

Finally, you can install the library and its other dependencies with:

```shell
$ pip install /path/to/srnmininet/clone
```

## Additions to IPMininet

We extend the following network components of IPMininet:

- IPTopo -> [SRNTopo](srnmininet/srntopo.py)
- IPNet -> [SRNNet](srnmininet/srnnet.py)
- Router -> [SRNRouter](srnmininet/srnrouter.py)
- IPHost -> [SRNHost](srnmininet/srnhost.py)
- IPIntf -> [SRNIntf](srnmininet/link.py)
- Named -> [SNRNamed](srnmininet/config/config.py)

The [IPMininet's documentation](https://ipmininet.readthedocs.io/en/latest/index.html)
is valid for SRNMininet but every extended component
has to be replaced by its extension to benefit from SRNMininet.

SRNMininet defines the following [additional daemons](srnmininet/config/config.py):

- OVSDB: a daemon configuring and running an OVSDB server
- SRNOSPF6: a daemon launching an OSPF6 daemon with SRN extensions for the controller to read IGP state
- SRCtrl: the SDN controller
- SRDNSProxy: the DNS proxy that interfaces the client with the DNS server and the controller
- SRRouted: the SRN daemon that setup SRv6 policies on access routers

In most cases, you will be able to launch a SRN by only instantiating
an SRCtrlDomain.
The topologies SquareAxA and CompTopo are examples for that.

## Scripts for SRN testing

[cfg_helper.py](scripts/cfg_helper.py) is a script to run an arbitrary SRN topology.
[test_srn.py](scripts/test_srn.py) compiles a few tests to perform on an emulated SRN.
