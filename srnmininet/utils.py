

def daemon_in_node(node, daemon_type):
    for daemon in node.config.daemons:
        if daemon.NAME == daemon_type.NAME:
            return daemon
    return None
