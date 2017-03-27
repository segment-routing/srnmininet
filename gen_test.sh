#!/bin/bash

ovsdb_client='ovsdb-client'
ovsdb_server='tcp:[::1]:6640'
ovsdb_database='SR_test'

function ovsdb_insert() {
	$ovsdb_client transact $ovsdb_server "[\"$ovsdb_database\", {\"op\": \"insert\", \"table\": \"$1\", \"row\": {$2}}]"
}

function add_node() {
	ovsdb_insert NodeState '"name": "'$1'", "addr": "'$2'", "prefix": "'$3'", "pbsid": "'$4'"'
}

function add_link() {
	ovsdb_insert LinkState '"name1": "'$1'", "addr1": "'$2'", "name2": "'$3'", "addr2": "'$4'", "metric": '$5', "bw": '$6', "ava_bw": '$7', "delay": '$8
}

function add_flowreq() {
	ovsdb_insert FlowReq '"destination": "'$1'", "dstaddr": "'$2'", "source": "'$3'", "bandwidth": '$4', "delay": '$5', "router": "'$6'", "status": '$7
}

function create_net1() {
	add_node A fc00::1 fc10::/48 fc00:1::/64
	add_node B fc01::1 fc11::/48 fc01:1::/64
	add_node C fc02::1 fc12::/48 fc02:1::/64
	add_node D fc03::1 fc13::/48 fc03:1::/64
	add_node E fc04::1 "" fc04:1::/64
	add_node F fc05::1 fc15::/48 fc05:1::/64
	add_node G fc06::1 fc16::/48 fc06:1::/64
	add_node H fc07::1 fc17::/48 fc07:1::/64
	add_node I fc08::1 fc18::/48 fc08:1::/64

	add_link A fd00::1 B fd00::2 1 100 100 1
	add_link B fd01::1 C fd01::2 1 100 100 1
	add_link A fd02::1 D fd02::2 1 100 100 1
	add_link B fd03::1 E fd03::2 1 100 100 1
	add_link C fd04::1 F fd04::2 1 100 100 1
	add_link D fd05::1 E fd05::2 1 100 100 1
	add_link E fd06::1 F fd06::2 1 100 100 1
	add_link D fd07::1 G fd07::2 1 100 100 1
	add_link E fd08::1 H fd08::2 1 100 100 1
	add_link F fd09::1 I fd09::2 1 100 100 1
	add_link G fd0a::1 H fd0a::2 1 100 100 1
	add_link H fd0b::1 I fd0b::2 1 100 100 1
}

# build upon nanonet SRTest topo
function create_net2() {
	add_node A fc00:2:0:1::1 fc00:2:0:1::/64 fc00:2:0:1::/64
	add_node B fc00:2:0:3::1 fc00:2:0:3::/64 fc00:2:0:3::/64
	add_node C fc00:2:0:2::1 fc00:2:0:2::/64 fc00:2:0:2::/64
	add_node D fc00:2:0:5::1 fc00:2:0:5::/64 fc00:2:0:5::/64
	add_node E fc00:2:0:4::1 fc00:2:0:4::/64 fc00:2:0:4::/64
	add_node F fc00:2:0:7::1 fc00:2:0:7::/64 fc00:2:0:7::/64
	add_node G fc00:2:0:6::1 fc00:2:0:6::/64 fc00:2:0:6::/64
	add_node H fc00:2:0:9::1 fc00:2:0:9::/64 fc00:2:0:9::/64
	add_node I fc00:2:0:8::1 fc00:2:0:8::/64 fc00:2:0:8::/64

	add_link A fc00:42:0:1::1 B fc00:42:0:1::2 1 100 100 1
	add_link B fc00:42:0:2::1 C fc00:42:0:2::2 1 100 100 1
	add_link A fc00:42:0:3::1 D fc00:42:0:3::2 1 100 100 1
	add_link B fc00:42:0:4::1 E fc00:42:0:4::2 1 100 100 1
	add_link C fc00:42:0:5::1 F fc00:42:0:5::2 1 100 100 1
	add_link D fc00:42:0:6::1 E fc00:42:0:6::2 1 100 100 1
	add_link E fc00:42:0:7::1 F fc00:42:0:7::2 1 100 100 1
	add_link D fc00:42:0:8::1 G fc00:42:0:8::2 1 100 100 1
	add_link E fc00:42:0:9::1 H fc00:42:0:9::2 1 100 100 1
	add_link F fc00:42:0:a::1 I fc00:42:0:a::2 1 100 100 1
	add_link G fc00:42:0:b::1 H fc00:42:0:b::2 1 100 100 1
	add_link H fc00:42:0:c::1 I fc00:42:0:c::2 1 100 100 1
}

function create_net3() {
	add_node A fc00:2:0:1::1 "fc00:2:0:1::/64;fc00:2:0:4::/64" fc00:2:0:1::/64
	add_node B fc00:2:0:3::1 fc00:2:0:3::/64 fc00:2:0:3::/64
	add_node C fc00:2:0:2::1 fc00:2:0:2::/64 fc00:2:0:2::/64
	add_node D fc00:2:0:5::1 fc00:2:0:5::/64 fc00:2:0:5::/64
	add_node E fc00:2:0:b::1 fc00:2:0:b::/64 fc00:2:0:b::/64
	add_node F fc00:2:0:7::1 fc00:2:0:7::/64 fc00:2:0:7::/64
	add_node G fc00:2:0:6::1 fc00:2:0:6::/64 fc00:2:0:6::/64
	add_node H fc00:2:0:9::1 fc00:2:0:9::/64 fc00:2:0:9::/64
	add_node I fc00:2:0:8::1 "fc00:2:0:8::/64;fc00:2:0:a::/64" fc00:2:0:8::/64

	add_link A fc00:42:0:1::1 B fc00:42:0:1::2 1 100 100 1
	add_link B fc00:42:0:2::1 C fc00:42:0:2::2 1 100 100 1
	add_link A fc00:42:0:3::1 D fc00:42:0:3::2 1 100 100 1
	add_link B fc00:42:0:4::1 E fc00:42:0:4::2 1 100 100 1
	add_link C fc00:42:0:5::1 F fc00:42:0:5::2 1 100 100 1
	add_link D fc00:42:0:6::1 E fc00:42:0:6::2 1 100 100 1
	add_link E fc00:42:0:7::1 F fc00:42:0:7::2 1 100 100 1
	add_link D fc00:42:0:8::1 G fc00:42:0:8::2 1 100 100 1
	add_link E fc00:42:0:9::1 H fc00:42:0:9::2 1 100 100 1
	add_link F fc00:42:0:a::1 I fc00:42:0:a::2 1 100 100 1
	add_link G fc00:42:0:b::1 H fc00:42:0:b::2 1 100 100 1
	add_link H fc00:42:0:c::1 I fc00:42:0:c::2 1 100 100 1
}

function create_reqs1() {
	add_flowreq accessI fc18::42 accessA 0 0 A 0
}

create_net3
