ovsdb_client "${node["sr-routed"].ovsdb_client}"
ovsdb_server "${node["sr-routed"].ovsdb_server}"
ovsdb_database "${node["sr-routed"].ovsdb_database}"
iproute "${node["sr-routed"].iproute}"
vnhpref "${node["sr-routed"].vnhpref}"
ingress_iface "${node["sr-routed"].ingress_iface}"
ntransacts ${node["sr-routed"].ntransacts}
