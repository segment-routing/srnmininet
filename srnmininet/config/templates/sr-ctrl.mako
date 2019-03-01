ovsdb_client "${node["sr-ctrl"].ovsdb_client}"
ovsdb_server "${node["sr-ctrl"].ovsdb_server}"
ovsdb_database "${node["sr-ctrl"].ovsdb_database}"
rules_file "${node["sr-ctrl"].rules_file}"
worker_threads ${node["sr-ctrl"].worker_threads}
req_buffer_size ${node["sr-ctrl"].req_buffer_size}
ntransacts ${node["sr-ctrl"].ntransacts}
zlog_conf_file "${node["sr-ctrl"].zlog_cfg_filename}"

% for key in node["sr-ctrl"].extras:
    % if type(node["sr-ctrl"].extras[key]) == int:
${key} ${node["sr-ctrl"].extras[key]}
    % else:
${key} "${node["sr-ctrl"].extras[key]}"
    % endif
% endfor
