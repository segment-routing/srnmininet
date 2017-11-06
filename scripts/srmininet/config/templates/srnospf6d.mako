<%inherit file="ospf6d.mako"/>

<%block name="router">
  %if node.ospf6d.ovsdb_adv:
  ovsdb_adv ${node.ospf6d.ovsdb_proto} ${node.ospf6d.ovsdb_ip6} ${node.ospf6d.ovsdb_port} ${node.ospf6d.ovsdb_database}
  %endif
</%block>
