include "/etc/bind/named.conf.options";
include "/etc/bind/named.conf.local";
include "/etc/bind/named.conf.default-zones";

logging {
    channel output {
        file ${node.named.logfile};
        severity warning;
        print-severity yes;
        print-time yes;
    };
};

$TTL 60
@	IN	SOA	test.sr.	root. (
					2017010401
					10800
					900
					604800
					86400 )
	IN	NS	ns.test.sr.

ns	IN	AAAA	fc00:2:0:2::1
accessA	IN	AAAA	fc00:2:0:4::1
accessI	IN	AAAA	fc00:2:0:a::1
