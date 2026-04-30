##########################################################################
#
#	UV local install support
#	
#	This make file supports installing the standalone Python and 
#	packages into the local project directory. This is used for 
#	production builds where we don't want the project to link back to 
#	any particular user's home directory, which is where these files 
#	would normally be installed. Instea they are installed into the
#	.local directory of DATA_TRANSPORT_PATH. 
#
#	2026-04-30	Todd Valentic
#				Initial implementation
#
##########################################################################

export DATA_TRANSPORT_PATH ?= /opt/transport
export LOCAL_DIR = $(DATA_TRANSPORT_PATH)/.local
export UV_CACHE_DIR = $(LOCAL_DIR)/cache
export UV_PYTHON_INSTALL_DIR = $(LOCAL_DIR)/python
export UV_PYTHON_BIN_DIR = $(LOCAL_DIR)/bin
export UV_PROJECT_ENVIRONMENT = $(DATA_TRANSPORT_PATH)/.venv
export PATH := $(UV_PYTHON_BIN_DIR):$(PATH)

.PHONY:	help setup

help:
	@echo
	@echo "Targets:"
	@echo
	@echo "  setup  Setup python and virtual env"
	@echo "  clean  Remove cache, venv"
	@echo "  help   List makefile target commands"
	@echo
	@echo "DATA_TRANSPORT_PATH is $(DATA_TRANSPORT_PATH)"
	@echo

setup:
	@mkdir -p $(UV_CACHE_DIR) 
	@mkdir -p $(UV_PYTHON_INSTALL_DIR) 
	@mkdir -p $(UV_PYTHON_BIN_DIR)

	@uv python install 
	@uv venv --clear
	@uv sync
	@restorecon -r /opt/transport/.venv/bin	
	@restorecon -r /opt/transport/.local

clean:
	@rm -rf $(LOCAL_DIR)
	@rm -rf $(UV_PROJECT_ENVIRONMENT)
