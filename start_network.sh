#!/bin/bash

echo "start_network.sh $1 $2 $3"

if [ $# -lt 1 ]; then
	echo "Please state if you want to clean start or restart the network"
	exit
fi

cd ~/sdnres-sigcomm
if [ $# -gt 1 ]; then
	if [ "$2" == "recompile" ] || [ "$2" == "clean" ]; then
		make clean
		sudo rm screenlog.0 sr-ctrl/screenlog.0 sr-dnsfwd/screenlog.0 sr-dnsproxy/screenlog.0 sr-routed/screenlog.0 c_tcp.pcap c_udp.pcap a_udp.pcap
	fi
	if [ "$2" == "compile" ] || [ "$2" == "recompile" ]; then
		make
	fi
fi
if [ "$1" == "stop" ] || [ "$1" == "restart" ]; then
	# Stop every "screened" process
	for namespace in "A" "C" "accessA"; do
		sudo ip netns exec $namespace pkill screen
		sudo pkill named
	done
	# Remove the namespaces
	sudo ip -all netns delete
	# Erase database
	rm srdb
fi
if [ "$1" == "restart" ] || [ "$1" == "start" ]; then
	# Create network namespaces
	if ! ip netns pids "A"; then
		sudo ./SRTest2.topo.sh
		sleep 2
	fi
	# Launch captures
	if [ "$2" == "debug" ] || [ "$3" == "debug" ]; then
		sudo ip netns exec "C" screen -d -m -L tcpdump -i any -w c_tcp.pcap tcp
		sudo ip netns exec "C" screen -d -m -L tcpdump -i any -w c_udp.pcap udp
		sudo ip netns exec "A" screen -d -m -L tcpdump -i any -w a_udp.pcap udp
	fi
	# Create the database + population
	echo "Launch ovsdb server"
	if ovsdb-tool create srdb sr.ovsschema; then
		sudo ip netns exec "C" screen -d -m -L ovsdb-server srdb --remote=ptcp:6640:[fc00:2:0:2::1] --remote=ptcp:6640:[::1] --unixctl=/home/vagrant/ovsdb.ctl
		sleep 3
		sudo ip netns exec "C" ./sr-ctrl/tests/gen_test.sh
	else
		sudo ip netns exec "C" screen -d -m -L ovsdb-server srdb --remote=ptcp:6640:[fc00:2:0:2::1] --remote=ptcp:6640:[::1] --unixctl=/home/vagrant/ovsdb.ctl
		sleep 3
	fi
	# Launch every program
	echo "Launch controller"
	cd ~/sdnres-sigcomm/sr-ctrl
	sudo ip netns exec "C" screen -d -m -L ./sr-ctrl ./tests/sr-ctrl.conf
	sleep 1
	echo "Launch dns proxy"
	cd ~/sdnres-sigcomm/sr-dnsproxy
	sudo ip netns exec "C" screen -d -m -L ./proxy sr-dnsproxy.conf
	sleep 1
	echo "Launch routing daemon"
	cd ~/sdnres-sigcomm/sr-routed
	sudo ip netns exec "A" screen -d -m -L ./sr-routed sr-routed.conf
	sleep 1
	echo "Launch dns forwarder"
	cd ~/sdnres-sigcomm/sr-dnsfwd
	sudo ip netns exec "A" screen -d -m -L ./dnsfwd sr-dnsfwd.conf
	sleep 1
	# Launch DNS server
	cd ~/sdnres-sigcomm
	if ! sudo ip netns exec "C" pkill -0 named; then
		echo "Launch dns server"
		sudo ip netns exec "C" screen -d -m -L /usr/sbin/named -u bind
	fi
	sleep 1
fi
