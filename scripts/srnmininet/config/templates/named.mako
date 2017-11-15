include "/etc/bind/named.conf.options";
include "/etc/bind/named.conf.local";
include "/etc/bind/named.conf.default-zones";

logging {
    channel output_file {
        file "${node.named.abs_logfile}";
        severity warning;
        print-severity yes;
        print-time yes;
    };
    category default { output_file; };
};

zone "${node.named.zone}" {
    type master;
    file "${node.named.zone_cfg_filename}";
};
