.PHONY: help build

SHELL:=/bin/bash
NAME?=datatransport-system
IMAGE?=$(NAME)
TAG?=2025-06
DATA_TRANSPORT_PATH=/opt/transport
TIMEOUT=300

help:
	@echo "Targets:"
	@echo ""
	@echo "  build     	create the container image"
	@echo "  clean   	stop the container and remove image" 
	@echo "  clean-all 	stop the container and remove image and volumes" 
	@echo "  shell     	run a user shell in the container"
	@echo "  root-shell	run a root shell in the container"
	@echo "  start     	start the container"
	@echo "  stop      	stop the container"
	@echo "  viewlog   	run viewlog in the container"
	@echo ""

build:
	podman build --tag $(IMAGE):$(TAG) -f Containerfile . 

shell:
	podman exec -it -u transport $(NAME) bash

root-shell:
	podman exec -it -w / -u root $(NAME) bash

start:
	podman run \
		--detach --rm \
		--name $(NAME) \
		--hostname $(NAME).local \
		--volume $(NAME)_app_log:/$(DATA_TRANSPORT_PATH)/log \
		--volume $(NAME)_app_var:/$(DATA_TRANSPORT_PATH)/var \
		--volume $(NAME)_app_groups:/$(DATA_TRANSPORT_PATH)/groups \
		--volume $(NAME)_inn_lib:/var/lib/news \
		--volume $(NAME)_inn_spool:/var/spool/news \
		$(IMAGE):$(TAG) 

stop:	
	podman stop --ignore --time $(TIMEOUT) $(NAME)

viewlog:
	podman exec -it $(NAME) viewlog -r

clean: stop
	podman rmi --force $(IMAGE):$(TAG)

clean-all: clean 
	podman volume rm --force $(NAME)_app_log  
	podman volume rm --force $(NAME)_app_var
	podman volume rm --force $(NAME)_app_groups
	podman volume rm --force $(NAME)_inn_lib
	podman volume rm --force $(NAME)_inn_spool

