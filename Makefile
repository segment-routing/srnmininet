
SCRIPTS=scripts/
CONFIG_HELPER=cfg_helper.py

VIRT_DIR=../srv6-virtenv
SRC_DIR="../dns-ctrl-uc/sigcomm/sdnres-sigcomm/"
SUBDIR=$(shell date "+%d-%m-%Y_%Z_%H:%M:%S.%N")/
LOG_DIR=log/$(SUBDIR)/

PIDFILE=cfg_helper.pid

TOPOLOGY=SquareAxA
LOG_LEVEL=info

.PHONY: compile clean start stop restart
.DEFAULT_GOAL: compile

compile:
	$(MAKE) -C $(SRC_DIR)

clean:
	$(MAKE) -C $(SRC_DIR) clean

start:
	$(MAKE) stop
	@echo "Launch everything"
	python $(SCRIPTS)/$(CONFIG_HELPER) --topo $(TOPOLOGY) --log $(LOG_LEVEL) --src-dir $(SRC_DIR) --log-dir $(LOG_DIR) --pid $(PIDFILE)

stop:
	if [ -f $(PIDFILE) ]; then \
		kill -s INT $(shell cat $(PIDFILE)); \
		rm $(PIDFILE); \
	fi

restart:
	$(MAKE) stop
	$(MAKE) start
