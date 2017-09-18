hostname ${node.name}
password ${node.password}

% if node.srnzebra.logfile:
    log file ${node.srnzebra.logfile}
% endif

% for section in node.srnzebra.debug:
    debug zebra ${section}
% endfor

% for itf in node.srnzebra.interfaces:
interface ${itf.name}
  no shutdown
  description ${itf.description}
  link-detect
  <%block name="interface"/>
!
% endfor

% for acl in node.srnzebra.access_lists:
    % for entry in acl:
${ip_statement(entry.prefix)} ${acl.acl_type} ${acl.name} ${entry.action} ${entry.prefix.with_prefixlen}
    % endfor
% endfor

% for rm in node.srnzebra.route_maps:
    % for entry in rm:
${rm.describe} ${rm.name} ${entry.action} ${entry.prio}
        % for acl in entry:
  match ${ip_statement(acl.prefix)} address ${acl.acl_type} ${acl.prefix.with_prefixlen}
        % endfor
  <%block name="routemap"/>
    % endfor
!
    % for proto in rm.proto:
ip protocol ${proto} route-map ${rm.name}
    % endfor
% endfor
!
% for route in node.srnzebra.static_routes:
${ip_statement(route.prefix)} route ${route.prefix} ${route.nexthop}
% endfor
