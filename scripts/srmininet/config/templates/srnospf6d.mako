hostname ${node.name}
password ${node.password}

% if node.srnospf6d.logfile:
log file ${node.srnospf6d.logfile}
% endif

% for section in node.srnospf6d.debug:
debug ospf6 section
% endfor

% for intf in node.srnospf6d.interfaces:
interface ${intf.name}
# ${intf.description}
  # Highiest priority routers will be DR
  ipv6 ospf6 priority ${intf.priority}
  ipv6 ospf6 cost ${intf.cost}
  % if not intf.passive and intf.active:
  ipv6 ospf6 dead-interval ${intf.dead_int}
  ipv6 ospf6 hello-interval ${intf.hello_int}
  % else:
  ipv6 ospf6 passive
  % endif
  ipv6 ospf6 instance-id ${intf.instance_id}
  <%block name="interface"/>
!
% endfor

router ospf6
  router-id ${node.srnospf6d.routerid}
  % for itf in node.srnospf6d.interfaces:
  interface ${itf.name} area ${itf.area}
  % endfor

  <%block name="router"/>
!
