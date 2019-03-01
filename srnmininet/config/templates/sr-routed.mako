ovsdb_client "${node["sr-routed"].ovsdb_client}"
ovsdb_server "${node["sr-routed"].ovsdb_server}"
ovsdb_database "${node["sr-routed"].ovsdb_database}"
router_name "${node["sr-routed"].router_name}"
localsid ${node["sr-routed"].localsid}
ingress_iface "${node["sr-routed"].ingress_iface}"
ntransacts ${node["sr-routed"].ntransacts}
zlog_conf_file "${node["sr-routed"].zlog_cfg_filename}"

% for key in node["sr-routed"].extras:
    % if type(node["sr-routed"].extras[key]) == int:
${key} ${node["sr-routed"].extras[key]}
    % else:
${key} "${node["sr-routed"].extras[key]}"
    % endif
% endfor
