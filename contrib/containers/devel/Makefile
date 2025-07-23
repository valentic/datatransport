.PHONY: help build create remove remove-all start stop shell root-shell logs top

SHELL:=/bin/bash

NAME?=datatransport-devel
IMAGE=$(NAME)
TAG?=2025-07

POD=$(NAME)-pod

CONTAINER_TRANSPORT=$(NAME)-main
CONTAINER_DATABASE=$(NAME)-postgresql

VOLUME_DATABASE=$(NAME)_db
VOLUME_TRANSPORT=$(NAME)_transport

DATA_TRANSPORT_PATH=/opt/transport
TIMEOUT=30

help:
	@echo "Targets:"
	@echo ""
	@echo "  build     	build the container images"
	@echo "  create    	create the pod, volumes and containers"
	@echo "  remove   	remove the pod and containers (keep volumes)"
	@echo "  remove-all remove the pod, containers and volumes" 
	@echo "  start     	start the pod"
	@echo "  stop      	stop the pod" 
	@echo "  shell     	run a user shell in the main container"
	@echo "  root-shell	run a root shell in the main container"
	@echo "  viewlog   	run transport viewlog"
	@echo "  logs		view the pod logs"
	@echo "  tops		view the pod processes"
	@echo ""

build:
	podman build --tag $(IMAGE):$(TAG) -f Containerfile . 

create:
	podman volume create \
		--ignore \
		$(VOLUME_DATABASE)
	podman pod create \
		--replace \
		--name $(POD)
	podman container create \
		--replace \
		--rm \
		--name $(CONTAINER_TRANSPORT) \
		--pod $(POD) \
		--volume $(VOLUME_TRANSPORT):$(DATA_TRANSPORT_PATH) \
		$(NAME):$(TAG)

shell:
	podman exec -it -w $(DATA_TRANSPORT_PATH)/groups -u transport $(CONTAINER_TRANSPORT) bash

root-shell:
	podman exec -it -w / -u root $(CONTAINER_TRANSPORT) bash

start:
	podman pod start $(POD)

stop:	
	podman pod stop --ignore --time $(TIMEOUT) $(POD)

logs:
	podman pod logs $(POD)

top:
	podman pod top $(POD)

viewlog:
	podman exec -it $() viewlog -r

remove: stop
	podman container rm --force $(CONTAINER_TRANSPORT)
	podman pod rm --force $(POD)

remove-image: stop
	podman rmi --force $(IMAGE):$(TAG)

remove-all: remove 
	podman volume rm --force $(NAME)_app_log  
	podman volume rm --force $(NAME)_app_var
	podman volume rm --force $(NAME)_app_groups

