
SCRIPTS=scripts/
CONFIG_HELPER=cfg_helper.py

VIRT_DIR=../srv6-virtenv
SRC_DIR="../dns-ctrl-uc/sigcomm/sdnres-sigcomm/"
SUBDIR=$(shell date "+%d-%m-%Y_%Z_%H:%M:%S.%N")/
# Problems may arise if it is a shared folder
LOG_DIR=../../log/$(SUBDIR)/

PIDFILE=cfg_helper.pid

TOPOLOGY=SquareAxA
LOG_LEVEL=info

.PHONY: compile clean start
.DEFAULT_GOAL: compile

compile:
	$(MAKE) -C $(SRC_DIR)

clean:
	$(MAKE) -C $(SRC_DIR) clean

start:
	sudo bash -c 'source /etc/profile && python $(SCRIPTS)/$(CONFIG_HELPER) --topo $(TOPOLOGY) --log $(LOG_LEVEL) --src-dir $(SRC_DIR) --log-dir $(LOG_DIR)'

light-start:
	sudo bash -c 'source /etc/profile && python $(SCRIPTS)/$(CONFIG_HELPER) --topo $(TOPOLOGY) --log $(LOG_LEVEL) --src-dir $(SRC_DIR) --log-dir $(LOG_DIR) --net-args static_routing=True'
