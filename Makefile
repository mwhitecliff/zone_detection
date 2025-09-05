SHELL := /bin/bash

.PHONY: start stop logs health

# Wurzelverzeichnis des Projekts relativ zu diesem Makefile
ROOT_DIR := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))

start:
	@bash "$(ROOT_DIR)scripts/start_backend.sh"

stop:
	@bash "$(ROOT_DIR)scripts/stop_backend.sh"

logs:
	@tail -n 200 "$(ROOT_DIR)backend/backend.log" || true

health:
	@curl -fsS http://127.0.0.1:5000/healthz && echo || true


