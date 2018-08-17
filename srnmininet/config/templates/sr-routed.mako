ovsdb_client "${node["sr-routed"].ovsdb_client}"
ovsdb_server "${node["sr-routed"].ovsdb_server}"
ovsdb_database "${node["sr-routed"].ovsdb_database}"
localsid ${node["sr-routed"].localsid}
ingress_iface "${node["sr-routed"].ingress_iface}"
ntransacts ${node["sr-routed"].ntransacts}
