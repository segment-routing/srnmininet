
SCRIPTS=scripts/
CONFIG_HELPER=cfg_helper.py

SRC_DIR=$(CURDIR)/../srn/
SUBDIR=$(shell date "+%d-%m-%Y_%Z-%H_%M_%S.%N")/
# Problems may arise if it is a shared folder
LOG_DIR=../log/$(SUBDIR)/

TOPOLOGY=SquareAxA
LOG_LEVEL=info

start:
	sudo bash -c 'source /etc/profile && python $(SCRIPTS)/$(CONFIG_HELPER) --topo $(TOPOLOGY) --log $(LOG_LEVEL) --src-dir $(SRC_DIR) --log-dir $(LOG_DIR)'

light-start:
	sudo bash -c 'source /etc/profile && python $(SCRIPTS)/$(CONFIG_HELPER) --topo $(TOPOLOGY) --log $(LOG_LEVEL) --src-dir $(SRC_DIR) --log-dir $(LOG_DIR) --net-args static_routing=True'

sr-testdns:
	# TODO Add patch to sr-routed

.PHONY: light-start clean start
.DEFAULT_GOAL: light-start
