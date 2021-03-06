ovsdb_client "${node["sr-dnsproxy"].ovsdb_client}"
ovsdb_server "${node["sr-dnsproxy"].ovsdb_server}"
ovsdb_database "${node["sr-dnsproxy"].ovsdb_database}"
router_name "${node["sr-dnsproxy"].router_name}"
max_queries ${node["sr-dnsproxy"].max_queries}
proxy_listen_addr "${node["sr-dnsproxy"].proxy_listen_addr}"
proxy_listen_port "${node["sr-dnsproxy"].proxy_listen_port}"
dns_server_port "${node["sr-dnsproxy"].dns_server_port}"
dns_server "${node["sr-dnsproxy"].dns_server}"
ntransacts ${node["sr-dnsproxy"].ntransacts}
client_server_fifo "${node["sr-dnsproxy"].client_server_fifo}"
zlog_conf_file "${node["sr-dnsproxy"].zlog_cfg_filename}"

% for key in node["sr-dnsproxy"].extras:
    % if type(node["sr-dnsproxy"].extras[key]) == int:
${key} ${node["sr-dnsproxy"].extras[key]}
    % else:
${key} "${node["sr-dnsproxy"].extras[key]}"
    % endif
% endfor
