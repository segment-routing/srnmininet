
$TTL 60
@	IN	SOA	${node.named.zone}	root. (
					2017010401
					10800
					900
					604800
					86400 )
	IN	NS	${node.name}.${node.named.zone}

% for ip6 in node.named.ns:
${node.name}	IN	AAAA	${ip6}
% endfor
% for host in node.named.hosts:
    % for ip6 in host.ip6s:
${host.name}	IN	AAAA	${ip6}
    % endfor
% endfor
