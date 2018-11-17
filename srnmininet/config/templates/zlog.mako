[formats]
timefmt = "%d(%d-%m (%T.ms)) %-5V [%p:%F:%L] %m%n"

[rules]
*.info    "${node["zlog"].logfile}"; timefmt
