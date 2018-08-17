
SCRIPTS=scripts/
CONFIG_HELPER=cfg_helper.py

SRC_DIR=$(CURDIR)/../srn/
SUBDIR=$(shell date "+%d-%m-%Y_%Z-%H_%M_%S.%N")/
# Problems may arise if it is a shared folder
LOG_DIR=../log/$(SUBDIR)/

TOPOLOGY=SquareAxA
LOG_LEVEL=info

.PHONY: light-start clean start sr-testdns
.DEFAULT_GOAL: light-start

start:
	sudo bash -c 'source /etc/profile && python $(SCRIPTS)/$(CONFIG_HELPER) --topo $(TOPOLOGY) --log $(LOG_LEVEL) --src-dir $(SRC_DIR) --log-dir $(LOG_DIR)'

light-start:
	sudo bash -c 'source /etc/profile && python $(SCRIPTS)/$(CONFIG_HELPER) --topo $(TOPOLOGY) --log $(LOG_LEVEL) --src-dir $(SRC_DIR) --log-dir $(LOG_DIR) --net-args static_routing=True'

test:
	sudo python $(SCRIPTS)/test_srn.py --log $(LOG_LEVEL) --src-dir $(SRC_DIR) --log-dir $(LOG_DIR)
