include "/etc/bind/named.conf.options";
include "/etc/bind/named.conf.local";
include "/etc/bind/named.conf.default-zones";

logging {
    channel output {
        file "${node.named.logfile}";
        severity warning;
        print-severity yes;
        print-time yes;
    };
};

zone "test.sr" {
    type master;
    file "test.sr.zone";
};
