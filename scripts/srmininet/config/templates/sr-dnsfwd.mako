logfile ${node["sr-dnsfwd"].logfile}
dns_fifo ${node["sr-dnsfwd"].dns_fifo}
router_name ${node["sr-dnsfwd"].router_name}
max_parallel_queries ${node["sr-dnsfwd"].max_parallel_queries}
proxy_listen_port ${node["sr-dnsfwd"].proxy_listen_port}
dns_proxy ${node["sr-dnsfwd"].dns_proxy}
dnsfwd_listen_port "${node["sr-dnsfwd"].dnsfwd_listen_port}
